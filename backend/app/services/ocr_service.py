"""
OCR Service for Part 4C: OCR + OpenCV + PaddleOCR
Provides optical character recognition, page-level traceability,
conservative image preprocessing, real confidence telemetry, and hybrid digital/OCR ingestion.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import fitz  # PyMuPDF
import numpy as np

from app.core.config import settings
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

# Cached OCR Engine instances (lazy loaded singletons)
_paddleocr_engine = None
_easyocr_engine = None


def get_paddleocr_engine():
    """Lazily initializes and caches the PaddleOCR engine."""
    global _paddleocr_engine
    if _paddleocr_engine is None:
        try:
            from paddleocr import PaddleOCR
            logger.info("Initializing PaddleOCR engine (lang=%s)...", settings.OCR_LANGUAGE)
            _paddleocr_engine = PaddleOCR(
                use_angle_cls=True,
                lang=settings.OCR_LANGUAGE,
                show_log=False,
            )
            logger.info("PaddleOCR engine initialized successfully.")
        except Exception as e:
            logger.warning("PaddleOCR initialization unavailable: %s", e)
            _paddleocr_engine = None
    return _paddleocr_engine


def get_easyocr_engine():
    """Lazily initializes and caches EasyOCR engine as resilient fallback."""
    global _easyocr_engine
    if _easyocr_engine is None:
        try:
            import easyocr
            logger.info("Initializing EasyOCR fallback engine (English, CPU)...")
            _easyocr_engine = easyocr.Reader(["en"], gpu=False, verbose=False)
            logger.info("EasyOCR fallback engine initialized successfully.")
        except Exception as e:
            logger.warning("EasyOCR fallback initialization failed: %s", e)
            _easyocr_engine = None
    return _easyocr_engine


def get_active_ocr_engine():
    """
    Returns the primary OCR engine according to system configuration.
    Defaults to PaddleOCR; falls back to EasyOCR if PaddleOCR is uninitialized.
    """
    preferred = (settings.OCR_ENGINE or "PADDLEOCR").upper()
    if preferred == "PADDLEOCR":
        engine = get_paddleocr_engine()
        if engine is not None:
            return "PADDLEOCR", engine
        # Fallback if PaddleOCR uninstalled/failed
        fallback = get_easyocr_engine()
        if fallback is not None:
            return "EASYOCR", fallback
        return None, None
    elif preferred == "EASYOCR":
        engine = get_easyocr_engine()
        if engine is not None:
            return "EASYOCR", engine
        fallback = get_paddleocr_engine()
        if fallback is not None:
            return "PADDLEOCR", fallback
        return None, None
    else:
        # Auto or default
        engine = get_paddleocr_engine() or get_easyocr_engine()
        engine_type = "PADDLEOCR" if engine == _paddleocr_engine else ("EASYOCR" if engine else None)
        return engine_type, engine


@dataclass
class OCRTextBlock:
    text: str
    confidence: Optional[float]
    bbox: Optional[List] = None


@dataclass
class PageOCRResult:
    page_number: int  # 1-indexed
    raw_text: str
    normalized_text: str
    extraction_method: str  # "DIGITAL_PDF" or "OCR"
    confidence: Optional[float]
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
    """Exception raised during OCR extraction errors with structured internal codes."""
    def __init__(self, error_code: str, error_message: str):
        super().__init__(error_message)
        self.error_code = error_code
        self.error_message = error_message


def run_ocr_on_image_matrix(img_matrix: np.ndarray) -> Tuple[str, Optional[float], List[OCRTextBlock]]:
    """
    Executes Optical Character Recognition on a preprocessed OpenCV image matrix.
    Uses PaddleOCR (or configured OCR engine) without fabricating confidence scores or coordinates.
    Returns (combined_text, average_confidence, text_blocks).
    """
    if img_matrix is None or img_matrix.size == 0:
        raise OCRExtractionError("INVALID_IMAGE_MATRIX", "Cannot run OCR on empty image matrix.")

    engine_type, engine = get_active_ocr_engine()
    if engine is None:
        raise OCRExtractionError(
            "OCR_ENGINE_UNAVAILABLE",
            "The optical character recognition engine could not be initialized.",
        )

    blocks: List[OCRTextBlock] = []
    lines: List[str] = []
    confidences: List[float] = []

    try:
        if engine_type == "PADDLEOCR":
            # PaddleOCR returns a list of results per image: [ [ [bbox, (text, conf)], ... ] ]
            ocr_res = engine.ocr(img_matrix, cls=True)
            if ocr_res and len(ocr_res) > 0 and ocr_res[0] is not None:
                for line in ocr_res[0]:
                    if len(line) >= 2:
                        bbox = line[0] if isinstance(line[0], (list, tuple)) else None
                        text_info = line[1]
                        if isinstance(text_info, (tuple, list)) and len(text_info) >= 2:
                            text, prob = str(text_info[0]).strip(), float(text_info[1])
                        elif isinstance(text_info, str):
                            text, prob = text_info.strip(), None
                        else:
                            continue

                        if text:
                            blocks.append(OCRTextBlock(text=text, confidence=prob, bbox=bbox))
                            lines.append(text)
                            if prob is not None:
                                confidences.append(prob)

        elif engine_type == "EASYOCR":
            # EasyOCR returns list of (bbox, text, prob)
            ocr_res = engine.readtext(img_matrix)
            for item in ocr_res:
                if len(item) >= 3:
                    bbox, text, prob = item[0], str(item[1]).strip(), float(item[2])
                    if text:
                        blocks.append(OCRTextBlock(text=text, confidence=prob, bbox=bbox))
                        lines.append(text)
                        confidences.append(prob)

    except Exception as e:
        logger.error("Error executing OCR model inference (%s): %s", engine_type, e)
        raise OCRExtractionError(
            "OCR_PROCESSING_FAILED",
            "An error occurred during optical character recognition inference.",
        )

    combined_text = "\n".join(lines).strip()
    avg_conf = float(np.mean(confidences)) if confidences else (None if not lines else 0.0)

    return combined_text, avg_conf, blocks


def process_page(
    pdf_bytes: bytes,
    page_number: int,
    dpi: Optional[int] = None,
) -> PageOCRResult:
    """
    Renders an individual 1-indexed PDF page, applies OpenCV preprocessing,
    executes OCR, and returns structured page extraction result.
    """
    try:
        page_img_bgr = render_pdf_page_to_image(pdf_bytes, page_number, dpi=dpi)
        preprocessed_img = preprocess_document_image(
            page_img_bgr,
            enhance_contrast=True,
            denoise=True,
            apply_deskew=settings.OCR_ENABLE_DESKEW,
        )
        ocr_text, avg_conf, blocks = run_ocr_on_image_matrix(preprocessed_img)
    except ImagePreprocessingError as ipe:
        logger.warning("Image preprocessing failed on page %d: %s", page_number, ipe)
        raise OCRExtractionError(ipe.error_code, ipe.error_message)
    except Exception as e:
        logger.warning("OCR failed on page %d: %s", page_number, e)
        ocr_text, avg_conf, blocks = "", None, []

    ocr_norm = normalize_extracted_text(ocr_text)

    return PageOCRResult(
        page_number=page_number,
        raw_text=ocr_text,
        normalized_text=ocr_norm,
        extraction_method="OCR",
        confidence=avg_conf,
        blocks=blocks,
    )


def process_document_with_ocr(
    file_bytes: bytes,
    mime_type: Optional[str] = None,
    filename: Optional[str] = None,
    dpi: Optional[int] = None,
) -> DocumentOCRResult:
    """
    Universal OCR & Hybrid Ingestion Engine for Part 4C:
    - Standalone images (PNG, JPG, JPEG): OpenCV Preprocessing -> PaddleOCR -> Single-page result
    - Multi-page PDFs:
        * Pages with usable digital text -> PyMuPDF digital extraction (Method: DIGITAL_PDF, Conf: 1.0)
        * Scanned / image-only pages -> PyMuPDF render -> OpenCV preprocessing -> PaddleOCR (Method: OCR)
    - Sets extraction method to DIGITAL_PDF, OCR, or HYBRID
    - Normalizes text while preserving statutory PAN, GSTIN, Udyam, currency (₹), and dates
    - Returns 1-indexed traceable page boundaries [PAGE 1], [PAGE 2], ...
    - Real confidence telemetry without fabricated values
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
            preprocessed_img = preprocess_document_image(
                img_bgr,
                enhance_contrast=True,
                denoise=True,
                apply_deskew=settings.OCR_ENABLE_DESKEW,
            )
            ocr_text, avg_conf, blocks = run_ocr_on_image_matrix(preprocessed_img)
        except ImagePreprocessingError as ipe:
            raise OCRExtractionError(ipe.error_code, ipe.error_message)

        norm_text = normalize_extracted_text(ocr_text)
        non_ws_count = len(re.sub(r"\s+", "", norm_text))
        is_low_quality = (non_ws_count < 10) or (avg_conf is not None and avg_conf < 0.25 and len(norm_text) > 0)
        if is_low_quality:
            quality_label = "Low / Unreadable Scan"
        elif avg_conf is not None and avg_conf > 0:
            quality_label = f"OCR Quality: {int(avg_conf * 100)}%"
        else:
            quality_label = "Low / Unreadable Scan"


        page_res = PageOCRResult(
            page_number=1,
            raw_text=ocr_text,
            normalized_text=norm_text,
            extraction_method="OCR",
            confidence=avg_conf,
            blocks=blocks,
        )

        formatted_raw = f"[PAGE 1]\n{ocr_text}" if ocr_text else ""
        formatted_norm = f"[PAGE 1]\n{norm_text}" if norm_text else ""

        return DocumentOCRResult(
            page_count=1,
            raw_text=formatted_raw,
            normalized_text=formatted_norm,
            extraction_method="OCR",
            average_ocr_confidence=avg_conf,
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
                raw_pages_text.append(f"[PAGE {page_num}]\n{digital_raw}")
                if digital_norm:
                    norm_pages_text.append(f"[PAGE {page_num}]\n{digital_norm}")
            else:
                # Page is scanned image -> Render page and execute OCR
                has_ocr_pages = True
                page_res = process_page(file_bytes, page_num, dpi=dpi)
                pages_result.append(page_res)
                if page_res.confidence is not None:
                    ocr_confidences.append(page_res.confidence)

                raw_pages_text.append(f"[PAGE {page_num}]\n{page_res.raw_text}")
                if page_res.normalized_text:
                    norm_pages_text.append(f"[PAGE {page_num}]\n{page_res.normalized_text}")

        # Determine overall document extraction method
        if has_digital_pages and has_ocr_pages:
            overall_method = "HYBRID"
        elif has_ocr_pages:
            overall_method = "OCR"
        else:
            overall_method = "DIGITAL_PDF"

        combined_raw = "\n\n".join(raw_pages_text).strip()
        combined_norm = "\n\n".join(norm_pages_text).strip()

        # Real aggregate OCR confidence (calculated strictly from OCR results, or None if purely digital)
        if ocr_confidences:
            overall_avg_conf = float(np.mean(ocr_confidences))
        elif has_digital_pages:
            overall_avg_conf = 1.0 if overall_method == "DIGITAL_PDF" else None
        else:
            overall_avg_conf = None

        non_ws_total = len(re.sub(r"\s+", "", combined_norm))
        is_low_quality = (non_ws_total < 10) or (overall_avg_conf is not None and overall_avg_conf < 0.25 and len(combined_norm) > 0)

        if overall_method == "DIGITAL_PDF":
            quality_label = "Digital PDF (Text Extracted)"
        elif is_low_quality:
            quality_label = "Low / Unreadable Scan"
        elif overall_avg_conf is not None and overall_avg_conf > 0:
            quality_label = f"OCR Quality: {int(overall_avg_conf * 100)}%"
        else:
            quality_label = "Low / Unreadable Scan"


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
