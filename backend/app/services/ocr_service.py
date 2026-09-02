"""
OCR Service for Part 4C: OCR & Image Preprocessing
Provides deep-learning optical character recognition, page-level traceability,
hybrid digital/OCR document processing, and confidence score calculation.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import fitz  # PyMuPDF
import numpy as np

from app.services.image_preprocessing_service import (
    ImagePreprocessingError,
    load_image_bytes_to_cv2,
    preprocess_document_image,
    render_pdf_page_to_image,
    calculate_image_sharpness,
)
from app.services.pdf_extraction_service import (
    analyze_text_quality,
    normalize_extracted_text,
    MIN_TEXT_CHARACTERS,
    MIN_CHARACTERS_PER_PAGE,
)

logger = logging.getLogger(__name__)

# Global cached OCR Reader instance (lazy loaded)
_easyocr_reader = None


def get_ocr_reader():
    """Lazily initializes and caches EasyOCR reader for English procurement documents."""
    global _easyocr_reader
    if _easyocr_reader is None:
        try:
            import easyocr
            logger.info("Initializing EasyOCR reader (English, CPU mode)...")
            _easyocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
            logger.info("EasyOCR reader initialized successfully.")
        except Exception as e:
            logger.error("Failed to initialize EasyOCR reader: %s", e)
            _easyocr_reader = None
    return _easyocr_reader


@dataclass
class OCRTextBlock:
    text: str
    confidence: float
    bbox: Optional[List] = None


@dataclass
class PageOCRResult:
    page_number: int
    raw_text: str
    normalized_text: str
    extraction_method: str  # "DIGITAL_PDF" or "OCR"
    confidence: float
    blocks: List[OCRTextBlock] = field(default_factory=list)


@dataclass
class DocumentOCRResult:
    page_count: int
    raw_text: str
    normalized_text: str
    extraction_method: str  # "OCR", "DIGITAL_PDF", "HYBRID"
    average_ocr_confidence: Optional[float]
    is_low_quality: bool
    quality_label: str
    pages: List[PageOCRResult] = field(default_factory=list)


class OCRExtractionError(Exception):
    """Exception raised during OCR extraction errors."""
    def __init__(self, error_code: str, error_message: str):
        super().__init__(error_message)
        self.error_code = error_code
        self.error_message = error_message


def run_ocr_on_image_matrix(img_matrix: np.ndarray) -> Tuple[str, float, List[OCRTextBlock]]:
    """
    Runs optical character recognition on a preprocessed OpenCV image matrix.
    Returns (combined_text, average_confidence, text_blocks).
    """
    reader = get_ocr_reader()
    if reader is None:
        raise OCRExtractionError(
            "OCR_INITIALIZATION_FAILED",
            "The optical character recognition engine could not be initialized.",
        )

    try:
        results = reader.readtext(img_matrix)
    except Exception as e:
        logger.error("Error executing OCR model inference: %s", e)
        raise OCRExtractionError(
            "OCR_PROCESSING_FAILED",
            "An error occurred during optical character recognition inference.",
        )

    blocks: List[OCRTextBlock] = []
    lines: List[str] = []
    confidences: List[float] = []

    for item in results:
        # EasyOCR returns (bbox, text, prob)
        if len(item) >= 3:
            bbox, text, prob = item[0], str(item[1]).strip(), float(item[2])
            if text:
                blocks.append(OCRTextBlock(text=text, confidence=prob, bbox=bbox))
                lines.append(text)
                confidences.append(prob)

    combined_text = "\n".join(lines).strip()
    avg_conf = float(np.mean(confidences)) if confidences else 0.0

    return combined_text, avg_conf, blocks


def process_document_with_ocr(
    file_bytes: bytes,
    mime_type: Optional[str] = None,
    filename: Optional[str] = None,
) -> DocumentOCRResult:
    """
    Universal OCR & Hybrid Ingestion Engine:
    - For images (PNG, JPG, JPEG): preprocessed with OpenCV -> OCR -> Single Page
    - For PDFs: analyzes digital text per page; runs OCR only on scanned/low-text pages
    - Assigns extraction_method: DIGITAL_PDF, OCR, or HYBRID
    - Normalizes text while preserving statutory PAN, GSTIN, Udyam, currency, and dates
    """
    if not file_bytes or len(file_bytes) == 0:
        raise OCRExtractionError("EMPTY_FILE", "The document binary contains 0 bytes.")

    fname = (filename or "").lower()
    mtype = (mime_type or "").lower()
    is_image = mtype in ["image/png", "image/jpeg", "image/jpg"] or fname.endswith((".png", ".jpg", ".jpeg"))

    # =========================================================================
    # Case A: Standalone Image File (PNG, JPG, JPEG)
    # =========================================================================
    if is_image:
        try:
            img_bgr = load_image_bytes_to_cv2(file_bytes)
            sharpness = calculate_image_sharpness(img_bgr)
            preprocessed_img = preprocess_document_image(img_bgr, enhance_contrast=True, denoise=True)
            ocr_text, avg_conf, blocks = run_ocr_on_image_matrix(preprocessed_img)
        except ImagePreprocessingError as ipe:
            raise OCRExtractionError(ipe.error_code, ipe.error_message)

        norm_text = normalize_extracted_text(ocr_text)
        non_ws_count = len(re.sub(r"\s+", "", norm_text))
        is_low_quality = (non_ws_count < 10) or (avg_conf < 0.25 and len(norm_text) > 0)
        quality_label = f"OCR Quality: {int(avg_conf * 100)}%" if avg_conf > 0 else "Low / Unreadable Scan"

        page_res = PageOCRResult(
            page_number=1,
            raw_text=ocr_text,
            normalized_text=norm_text,
            extraction_method="OCR",
            confidence=avg_conf,
            blocks=blocks,
        )

        formatted_raw = f"--- Page 1 ---\n{ocr_text}" if ocr_text else ""
        formatted_norm = f"--- Page 1 ---\n{norm_text}" if norm_text else ""

        return DocumentOCRResult(
            page_count=1,
            raw_text=formatted_raw,
            normalized_text=formatted_norm,
            extraction_method="OCR",
            average_ocr_confidence=avg_conf if avg_conf > 0 else None,
            is_low_quality=is_low_quality,
            quality_label=quality_label,
            pages=[page_res],
        )

    # =========================================================================
    # Case B: Multi-Page PDF Document (Scanned or Hybrid)
    # =========================================================================
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        logger.error("Failed to open PDF stream for OCR: %s", e)
        raise OCRExtractionError("PDF_CORRUPTED", "The PDF document is corrupted and could not be opened.")

    try:
        if doc.is_encrypted or doc.needs_pass:
            raise OCRExtractionError(
                "PASSWORD_PROTECTED_PDF",
                "This PDF is password protected. Upload an unlocked copy to continue processing.",
            )

        page_count = doc.page_count
        if page_count <= 0:
            raise OCRExtractionError("EMPTY_PDF", "The PDF document contains 0 pages.")

        pages_result: List[PageOCRResult] = []
        raw_pages_text: List[str] = []
        norm_pages_text: List[str] = []
        ocr_confidences: List[float] = []
        has_digital_pages = False
        has_ocr_pages = False

        for page_idx in range(page_count):
            page_num = page_idx + 1
            page = doc.load_page(page_idx)
            digital_raw = page.get_text("text") or ""
            digital_norm = normalize_extracted_text(digital_raw)

            # Check if this specific page has genuine selectable digital text
            is_digital, _ = analyze_text_quality(
                raw_text=digital_raw,
                page_count=1,
                min_text_chars=MIN_TEXT_CHARACTERS,
                min_chars_per_page=MIN_CHARACTERS_PER_PAGE,
            )

            if is_digital:
                # Use digital extraction for this page
                has_digital_pages = True
                page_res = PageOCRResult(
                    page_number=page_num,
                    raw_text=digital_raw,
                    normalized_text=digital_norm,
                    extraction_method="DIGITAL_PDF",
                    confidence=1.0,
                )
                pages_result.append(page_res)
                raw_pages_text.append(f"--- Page {page_num} ---\n{digital_raw}")
                if digital_norm:
                    norm_pages_text.append(f"--- Page {page_num} ---\n{digital_norm}")
            else:
                # Page is scanned image -> Render page and execute OCR
                has_ocr_pages = True
                try:
                    page_img_bgr = render_pdf_page_to_image(file_bytes, page_num, dpi=200)
                    preprocessed_img = preprocess_document_image(page_img_bgr, enhance_contrast=True, denoise=True)
                    ocr_text, avg_conf, blocks = run_ocr_on_image_matrix(preprocessed_img)
                except Exception as pe:
                    logger.warning("OCR failed on page %d: %s", page_num, pe)
                    ocr_text, avg_conf, blocks = "", 0.0, []

                ocr_norm = normalize_extracted_text(ocr_text)
                if avg_conf > 0:
                    ocr_confidences.append(avg_conf)

                page_res = PageOCRResult(
                    page_number=page_num,
                    raw_text=ocr_text,
                    normalized_text=ocr_norm,
                    extraction_method="OCR",
                    confidence=avg_conf,
                    blocks=blocks,
                )
                pages_result.append(page_res)
                raw_pages_text.append(f"--- Page {page_num} ---\n{ocr_text}")
                if ocr_norm:
                    norm_pages_text.append(f"--- Page {page_num} ---\n{ocr_norm}")

        # Determine overall document extraction method
        if has_digital_pages and has_ocr_pages:
            overall_method = "HYBRID"
        elif has_ocr_pages:
            overall_method = "OCR"
        else:
            overall_method = "DIGITAL_PDF"

        combined_raw = "\n\n".join(raw_pages_text).strip()
        combined_norm = "\n\n".join(norm_pages_text).strip()
        overall_avg_conf = float(np.mean(ocr_confidences)) if ocr_confidences else (1.0 if has_digital_pages else 0.0)

        non_ws_total = len(re.sub(r"\s+", "", combined_norm))
        is_low_quality = (non_ws_total < 10) or (overall_avg_conf < 0.25 and len(combined_norm) > 0)
        quality_label = f"OCR Quality: {int(overall_avg_conf * 100)}%" if overall_method != "DIGITAL_PDF" else "Digital PDF"

        return DocumentOCRResult(
            page_count=page_count,
            raw_text=combined_raw,
            normalized_text=combined_norm,
            extraction_method=overall_method,
            average_ocr_confidence=overall_avg_conf if overall_method != "DIGITAL_PDF" else None,
            is_low_quality=is_low_quality,
            quality_label=quality_label,
            pages=pages_result,
        )

    finally:
        doc.close()
