"""
PDF Extraction Service for Part 4B: PDF Text Extraction with PyMuPDF
Provides reliable text extraction from digital/text-based PDFs, text normalization,
traceable page-by-page mapping, text quality metrics, and OCR requirement detection.
"""

import re
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import fitz  # PyMuPDF

from app.db.models.document_processing import (
    DocumentProcessing,
    ExtractionMethod,
    ProcessingStage,
    ProcessingStatus,
)

logger = logging.getLogger(__name__)

# Configurable quality thresholds for deterministic digital vs. scanned PDF classification
MIN_TEXT_CHARACTERS = 50  # Minimum non-whitespace characters for whole document
MIN_CHARACTERS_PER_PAGE = 30  # Minimum non-whitespace characters per page average


class PDFExtractionError(Exception):
    """Custom exception with structured error code and user-facing message."""
    def __init__(self, error_code: str, error_message: str):
        super().__init__(error_message)
        self.error_code = error_code
        self.error_message = error_message


@dataclass
class PDFPageExtraction:
    page_number: int  # 1-indexed
    raw_text: str
    normalized_text: str
    character_count: int
    non_whitespace_count: int


@dataclass
class PDFExtractionResult:
    page_count: int
    raw_text: str
    normalized_text: str
    is_digital_pdf: bool
    is_ocr_required: bool
    extraction_method: str
    total_characters: int
    non_whitespace_characters: int
    characters_per_page: float
    pages: List[PDFPageExtraction] = field(default_factory=list)
    quality_metrics: Dict[str, any] = field(default_factory=dict)


def normalize_extracted_text(text: str) -> str:
    """
    Conservatively normalizes extracted PDF text without destroying statutory identifiers,
    financial values, dates, percentages, or punctuation.

    Preserves:
    - PAN numbers: ABCDE1234F
    - GSTIN: 33ABCDE1234F1Z5
    - Udyam registration: UDYAM-TN-00-1234567
    - Currency / Numbers: ₹5,00,00,000, 50%, 123.45
    - Dates: 2026-08-26, 26/08/2026
    - Line & page boundaries
    """
    if not text:
        return ""

    # 1. Normalize carriage returns to standard newlines
    clean = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Strip horizontal control characters while preserving printable UTF-8 symbols (₹, %, etc.)
    clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", clean)

    # 3. Normalize multiple spaces/tabs on the same line to a single space
    clean = re.sub(r"[ \t]+", " ", clean)

    # 4. Strip leading and trailing whitespace from each line
    lines = [line.strip() for line in clean.split("\n")]

    # 5. Collapse excessive blank lines (more than 2 consecutive newlines -> 2)
    collapsed_lines = []
    blank_count = 0
    for line in lines:
        if not line:
            blank_count += 1
            if blank_count <= 1:
                collapsed_lines.append("")
        else:
            blank_count = 0
            collapsed_lines.append(line)

    return "\n".join(collapsed_lines).strip()


def analyze_text_quality(
    raw_text: str,
    page_count: int,
    min_text_chars: int = MIN_TEXT_CHARACTERS,
    min_chars_per_page: int = MIN_CHARACTERS_PER_PAGE,
) -> Tuple[bool, Dict[str, any]]:
    """
    Deterministically analyzes text metrics to verify if the PDF contains genuine digital text
    or is a scanned image with minimal/zero embedded text.
    """
    total_chars = len(raw_text) if raw_text else 0
    non_ws_chars = len(re.sub(r"\s+", "", raw_text)) if raw_text else 0
    pages = max(1, page_count)
    chars_per_page = round(non_ws_chars / pages, 2)

    # A digital PDF must satisfy minimum overall non-whitespace characters and per-page density
    is_digital = (non_ws_chars >= min_text_chars) and (chars_per_page >= min_chars_per_page)

    metrics = {
        "total_characters": total_chars,
        "non_whitespace_characters": non_ws_chars,
        "page_count": page_count,
        "characters_per_page": chars_per_page,
        "is_digital_pdf": is_digital,
        "ocr_required": not is_digital,
        "quality_label": "High / Digital" if is_digital else "Low / Scanned Image",
    }

    return is_digital, metrics


def extract_pdf_text(
    file_bytes: bytes,
    filename: Optional[str] = None,
    min_text_chars: int = MIN_TEXT_CHARACTERS,
    min_chars_per_page: int = MIN_CHARACTERS_PER_PAGE,
) -> PDFExtractionResult:
    """
    Primary Step 4B extraction engine.
    Extracts text page-by-page from raw PDF binary bytes using PyMuPDF (fitz).
    Handles corruption, encryption, page validation, normalization, and OCR requirement detection.
    Page numbering is 1-indexed. Page boundaries are strictly preserved.
    """
    if not file_bytes or len(file_bytes) == 0:
        raise PDFExtractionError(
            error_code="EMPTY_FILE",
            error_message="The uploaded document binary is empty (0 bytes).",
        )

    # 1. Attempt to open document stream with PyMuPDF
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        logger.warning("PyMuPDF failed to open PDF stream for %s: %s", filename or "unnamed", e)
        raise PDFExtractionError(
            error_code="PDF_CORRUPTED",
            error_message="The PDF file is corrupted or formatted invalidly and could not be opened.",
        )

    try:
        # 2. Check encryption / password protection
        if doc.is_encrypted or doc.needs_pass:
            raise PDFExtractionError(
                error_code="PASSWORD_PROTECTED_PDF",
                error_message="This PDF is password protected. Upload an unlocked copy to continue processing.",
            )

        # 3. Check page count
        page_count = doc.page_count
        if page_count <= 0:
            raise PDFExtractionError(
                error_code="EMPTY_PDF",
                error_message="The PDF document contains 0 pages.",
            )

        # 4. Extract text page-by-page (1-indexed)
        raw_pages_text: List[str] = []
        normalized_pages_text: List[str] = []
        page_extractions: List[PDFPageExtraction] = []

        for page_idx in range(page_count):
            page_num = page_idx + 1
            try:
                page = doc.load_page(page_idx)
                page_raw = page.get_text("text") or ""
            except Exception as e:
                logger.warning("Error reading page %d of PDF %s: %s", page_num, filename or "", e)
                page_raw = ""

            page_norm = normalize_extracted_text(page_raw)
            non_ws = len(re.sub(r"\s+", "", page_raw))

            page_extractions.append(
                PDFPageExtraction(
                    page_number=page_num,
                    raw_text=page_raw,
                    normalized_text=page_norm,
                    character_count=len(page_raw),
                    non_whitespace_count=non_ws,
                )
            )

            # Format traceable page boundaries with [PAGE N] headers
            raw_pages_text.append(f"[PAGE {page_num}]\n{page_raw}")
            if page_norm:
                normalized_pages_text.append(f"[PAGE {page_num}]\n{page_norm}")

        combined_raw_text = "\n\n".join(raw_pages_text).strip()
        combined_norm_text = "\n\n".join(normalized_pages_text).strip()

        # 5. Evaluate Text Quality & Determine Digital vs Scanned
        is_digital, quality_metrics = analyze_text_quality(
            raw_text=combined_raw_text,
            page_count=page_count,
            min_text_chars=min_text_chars,
            min_chars_per_page=min_chars_per_page,
        )

        return PDFExtractionResult(
            page_count=page_count,
            raw_text=combined_raw_text if is_digital else "",
            normalized_text=combined_norm_text if is_digital else "",
            is_digital_pdf=is_digital,
            is_ocr_required=not is_digital,
            extraction_method=ExtractionMethod.DIGITAL_PDF if is_digital else ExtractionMethod.NONE,
            total_characters=quality_metrics["total_characters"],
            non_whitespace_characters=quality_metrics["non_whitespace_characters"],
            characters_per_page=quality_metrics["characters_per_page"],
            pages=page_extractions,
            quality_metrics=quality_metrics,
        )

    finally:
        doc.close()


# Alias for backward compatibility
extract_text_from_pdf_bytes = extract_pdf_text


def extract_pdf(
    doc: any,
    db: any,
    file_bytes: Optional[bytes] = None,
) -> DocumentProcessing:
    """
    High-level extraction function for an individual BidDocument.
    Executes PyMuPDF digital extraction and updates linked DocumentProcessing record.
    """
    from app.services.storage_service import storage_service

    proc = doc.processing
    if not proc:
        proc = DocumentProcessing(
            id=uuid.uuid4(),
            bid_document_id=doc.id,
            processing_status=ProcessingStatus.QUEUED,
            processing_stage=ProcessingStage.INGESTION,
            extraction_method=ExtractionMethod.NONE,
        )
        db.add(proc)
        db.commit()
        db.refresh(proc)

    # Set status to PROCESSING / TEXT_EXTRACTION
    proc.processing_status = ProcessingStatus.PROCESSING
    proc.processing_stage = ProcessingStage.TEXT_EXTRACTION
    proc.processing_started_at = datetime.now(timezone.utc)
    proc.error_code = None
    proc.error_message = None
    db.commit()

    if file_bytes is None:
        try:
            file_bytes = storage_service.download_file(doc.storage_path)
        except Exception as e:
            logger.error("Failed to download file from storage for document %s: %s", doc.id, e)
            proc.processing_status = ProcessingStatus.FAILED
            proc.processing_stage = ProcessingStage.INGESTION
            proc.error_code = "STORAGE_DOWNLOAD_FAILED"
            proc.error_message = "Failed to retrieve document binary from storage."
            proc.processing_completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(proc)
            return proc

    try:
        extraction_res = extract_pdf_text(
            file_bytes=file_bytes,
            filename=doc.original_filename or doc.document_name,
        )

        proc.page_count = extraction_res.page_count
        proc.raw_text = extraction_res.raw_text
        proc.normalized_text = extraction_res.normalized_text
        proc.processing_completed_at = datetime.now(timezone.utc)

        if extraction_res.is_digital_pdf:
            proc.extraction_method = ExtractionMethod.DIGITAL_PDF
            proc.processing_status = ProcessingStatus.COMPLETED
            proc.processing_stage = ProcessingStage.COMPLETED
            proc.error_code = None
            proc.error_message = None

            if proc.normalized_text:
                clean_norm = " ".join(proc.normalized_text.lower().split())
                proc.normalized_content_hash = hashlib.sha256(clean_norm.encode("utf-8")).hexdigest()
        else:
            # Scanned / image-only PDF with insufficient digital text
            proc.extraction_method = ExtractionMethod.NONE
            proc.processing_status = ProcessingStatus.NEEDS_REVIEW
            proc.processing_stage = ProcessingStage.TEXT_EXTRACTION
            proc.error_code = "PDF_NO_EXTRACTABLE_TEXT"
            proc.error_message = "This document contains little or no extractable digital text and may require OCR processing."

        db.commit()
        db.refresh(proc)
        return proc

    except PDFExtractionError as pe:
        proc.processing_status = ProcessingStatus.FAILED
        proc.processing_stage = ProcessingStage.TEXT_EXTRACTION
        proc.error_code = pe.error_code
        proc.error_message = pe.error_message
        proc.processing_completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(proc)
        return proc
    except Exception as e:
        logger.exception("Unexpected error during PDF extraction on document %s: %s", doc.id, e)
        proc.processing_status = ProcessingStatus.FAILED
        proc.processing_stage = ProcessingStage.TEXT_EXTRACTION
        proc.error_code = "PDF_TEXT_EXTRACTION_FAILED"
        proc.error_message = "An error occurred while extracting text from the PDF document."
        proc.processing_completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(proc)
        return proc
