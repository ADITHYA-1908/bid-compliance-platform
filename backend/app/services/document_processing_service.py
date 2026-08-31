"""
Document Processing Service for Part 4A, 4B, 4C, 4D & 4E
Provides centralized lifecycle orchestration, stage transitions, idempotency checks,
storage existence verification, PyMuPDF digital text extraction, OpenCV image preprocessing,
OCR text extraction, hybrid document processing, deterministic document classification,
structured entity/field extraction, and quality telemetry for bid compliance documents.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.document_processing import (
    ClassificationConfidenceLevel,
    DocumentClass,
    DocumentProcessing,
    ExtractionMethod,
    ProcessingStage,
    ProcessingStatus,
)
from app.db.models.profile import Profile
from app.db.models.user import User
from app.schemas.document_processing import (
    DocumentClassificationResponse,
    DocumentExtractedDataResponse,
    DocumentExtractedTextResponse,
    ExtractedFieldItem,
)
from app.services.bid_document_service import _get_bid_for_bidder
from app.services.pdf_extraction_service import (
    PDFExtractionError,
    extract_text_from_pdf_bytes,
)
from app.services.ocr_service import (
    OCRExtractionError,
    process_document_with_ocr,
)
from app.services.document_classification_service import (
    derive_expected_document_type,
    execute_document_classification,
)
from app.services.structured_extraction_service import (
    extract_structured_entities_from_text,
    StructuredExtractionResult,
)
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


def _get_document_for_bidder(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
) -> Tuple[Profile, Bid, BidDocument]:
    """
    Validates tenant ownership and retrieves the BidDocument with its linked processing record.
    Returns 404 if bid or document is not owned by the authenticated bidder.
    """
    profile, bid = _get_bid_for_bidder(db, current_user, bid_id)

    doc = db.scalars(
        select(BidDocument)
        .options(
            joinedload(BidDocument.tender_requirement),
            joinedload(BidDocument.processing),
        )
        .where(
            BidDocument.id == document_id,
            BidDocument.bid_id == bid.id,
        )
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or does not belong to this bid.",
        )

    return profile, bid, doc


def create_or_get_processing_record(
    db: Session,
    bid_document_id: uuid.UUID,
) -> DocumentProcessing:
    """
    Idempotently creates or retrieves the DocumentProcessing record for a BidDocument.
    Defaults to QUEUED status and INGESTION stage.
    """
    existing = db.scalars(
        select(DocumentProcessing).where(DocumentProcessing.bid_document_id == bid_document_id)
    ).first()

    if existing:
        return existing

    record = DocumentProcessing(
        id=uuid.uuid4(),
        bid_document_id=bid_document_id,
        processing_status=ProcessingStatus.QUEUED,
        processing_stage=ProcessingStage.INGESTION,
        extraction_method=ExtractionMethod.NONE,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_document_processing(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DocumentProcessing:
    """
    Retrieves the DocumentProcessing telemetry for a specific BidDocument.
    If the document exists but lacks a processing record (e.g. legacy document),
    it initializes a QUEUED record automatically.
    """
    _, _, doc = _get_document_for_bidder(db, current_user, bid_id, document_id)

    if doc.processing:
        return doc.processing

    return create_or_get_processing_record(db, doc.id)


def execute_document_processing_pipeline(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DocumentProcessing:
    """
    Master Ingestion, Extraction & Classification Engine for Part 4A, 4B, 4C & 4D:
    1. Verifies storage file binary existence.
    2. Enforces idempotency (if already processed with text and classified).
    3. Seamlessly routes:
       - Standalone images (PNG/JPG/JPEG): OpenCV Preprocessing -> OCR Engine
       - Digital PDFs: PyMuPDF extraction -> DIGITAL_PDF
       - Scanned / Image PDFs: OpenCV Preprocessing -> OCR Engine -> OCR
       - Hybrid PDFs (mixed digital & scan): Page-level routing -> HYBRID
    4. Automatically advances to CLASSIFICATION stage and executes deterministic document classifier.
    5. Flags low-quality scans / mismatches -> NEEDS_REVIEW with clear telemetry.
    6. Advances successfully classified documents to STRUCTURED_EXTRACTION (ready for Part 4E).
    """
    _, bid, doc = _get_document_for_bidder(db, current_user, bid_id, document_id)

    if not doc.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive or superseded documents cannot be processed.",
        )

    # 1. Verify storage binary existence
    if not storage_service.file_exists(doc.storage_path):
        proc = create_or_get_processing_record(db, doc.id)
        proc.processing_status = ProcessingStatus.FAILED
        proc.processing_stage = ProcessingStage.INGESTION
        proc.error_code = "FILE_NOT_FOUND"
        proc.error_message = "Document binary file was not found in storage."
        db.commit()
        db.refresh(proc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document binary file was not found in storage.",
        )

    proc = create_or_get_processing_record(db, doc.id)

    # 2. Idempotency Check: if already processed, classified, and extracted
    if (
        proc.extraction_method in [ExtractionMethod.DIGITAL_PDF, ExtractionMethod.OCR, ExtractionMethod.HYBRID]
        and proc.processing_stage == ProcessingStage.COMPLETED
        and proc.detected_document_type is not None
        and proc.extracted_data is not None
        and proc.raw_text
    ):
        return proc

    # 3. Transition to PROCESSING / TEXT_EXTRACTION
    proc.processing_status = ProcessingStatus.PROCESSING
    proc.processing_stage = ProcessingStage.TEXT_EXTRACTION
    proc.processing_started_at = datetime.now(timezone.utc)
    proc.error_code = None
    proc.error_message = None
    db.commit()

    # 4. Download document binary from private storage
    try:
        file_bytes = storage_service.download_file(doc.storage_path)
    except Exception as e:
        logger.error("Failed to download file bytes for document %s: %s", doc.id, e)
        proc.processing_status = ProcessingStatus.FAILED
        proc.processing_stage = ProcessingStage.INGESTION
        proc.error_code = "STORAGE_DOWNLOAD_FAILED"
        proc.error_message = "Failed to retrieve document binary from storage."
        db.commit()
        db.refresh(proc)
        return proc

    # 5. Execute OCR & Document Extraction Pipeline
    try:
        ocr_result = process_document_with_ocr(
            file_bytes=file_bytes,
            mime_type=doc.mime_type,
            filename=doc.original_filename,
        )

        proc.page_count = ocr_result.page_count
        proc.raw_text = ocr_result.raw_text
        proc.normalized_text = ocr_result.normalized_text
        proc.extraction_method = ocr_result.extraction_method

        # 6. Advance to CLASSIFICATION Stage (Part 4D)
        proc.processing_stage = ProcessingStage.CLASSIFICATION
        db.commit()

        # 7. Execute Deterministic Document Classification
        proc = execute_document_classification(
            db=db,
            document_processing=proc,
            bid_document=doc,
        )

        # 8. Advance to STRUCTURED_EXTRACTION Stage (Part 4E)
        proc.processing_stage = ProcessingStage.STRUCTURED_EXTRACTION
        db.commit()

        # 9. Execute Deterministic Structured Entity Extraction
        proc = execute_structured_extraction(
            db=db,
            document_processing=proc,
            bid_document=doc,
        )

        # 10. Finalize Processing Stage and Status
        proc.processing_stage = ProcessingStage.COMPLETED
        proc.processing_completed_at = datetime.now(timezone.utc)

        # Check review triggers across OCR, Classification, and Structured Extraction
        if ocr_result.is_low_quality:
            logger.warning(
                "Document %s processed with low OCR quality (%s). Marked as NEEDS_REVIEW.",
                doc.id,
                ocr_result.quality_label,
            )
            proc.processing_status = ProcessingStatus.NEEDS_REVIEW
            proc.error_code = "OCR_LOW_QUALITY"
            proc.error_message = f"Document scan quality is very low ({ocr_result.quality_label}). Manual review may be required."
        elif proc.classification_requires_review or proc.extraction_requires_review:
            proc.processing_status = ProcessingStatus.NEEDS_REVIEW
            if not proc.error_code:
                proc.error_code = "EXTRACTION_REQUIRES_REVIEW"
                proc.error_message = "Some extracted fields require manual review due to low confidence, missing mandatory fields, or conflicting values."
        else:
            proc.processing_status = ProcessingStatus.COMPLETED
            proc.error_code = None
            proc.error_message = None

        db.commit()
        db.refresh(proc)
        return proc

    except (OCRExtractionError, PDFExtractionError) as oe:
        logger.warning("Extraction error on document %s: [%s] %s", doc.id, oe.error_code, oe.error_message)
        proc.processing_status = ProcessingStatus.FAILED
        proc.processing_stage = ProcessingStage.OCR if doc.mime_type != "application/pdf" else ProcessingStage.TEXT_EXTRACTION
        proc.error_code = oe.error_code
        proc.error_message = oe.error_message
        proc.processing_completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(proc)
        return proc

    except Exception as e:
        logger.error("Unexpected error during document processing on %s: %s", doc.id, e)
        proc.processing_status = ProcessingStatus.FAILED
        proc.processing_stage = ProcessingStage.STRUCTURED_EXTRACTION if proc.processing_stage == ProcessingStage.STRUCTURED_EXTRACTION else ProcessingStage.TEXT_EXTRACTION
        proc.error_code = "STRUCTURED_EXTRACTION_FAILED" if proc.processing_stage == ProcessingStage.STRUCTURED_EXTRACTION else "PROCESSING_UNEXPECTED_ERROR"
        proc.error_message = "An unexpected error occurred while processing the document."
        proc.processing_completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(proc)
        return proc


# Alias for backward compatibility
def execute_pdf_text_extraction(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DocumentProcessing:
    return execute_document_processing_pipeline(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
    )


def queue_document_processing(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DocumentProcessing:
    """Queues and executes document processing pipeline."""
    return execute_document_processing_pipeline(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
    )


def retry_document_processing(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DocumentProcessing:
    """
    Retries processing on a FAILED or NEEDS_REVIEW document.
    Resets failure state and executes document processing pipeline.
    """
    _, _, doc = _get_document_for_bidder(db, current_user, bid_id, document_id)

    if not doc.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive or superseded documents cannot be queued for retry.",
        )

    proc = create_or_get_processing_record(db, doc.id)

    if proc.processing_status not in [ProcessingStatus.FAILED, ProcessingStatus.NEEDS_REVIEW]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only FAILED or NEEDS_REVIEW document processing can be retried. Current status is '{proc.processing_status}'.",
        )

    # Reset state
    proc.processing_status = ProcessingStatus.QUEUED
    proc.processing_stage = ProcessingStage.INGESTION
    proc.processing_started_at = None
    proc.processing_completed_at = None
    proc.error_code = None
    proc.error_message = None
    db.commit()
    db.refresh(proc)

    return execute_document_processing_pipeline(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
    )


def get_document_extracted_text(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DocumentExtractedTextResponse:
    """
    Retrieves the extracted text and quality telemetry for an authenticated bidder's document.
    Enforces strict tenant isolation.
    """
    _, bid, doc = _get_document_for_bidder(db, current_user, bid_id, document_id)

    proc = doc.processing or create_or_get_processing_record(db, doc.id)

    char_count = len(proc.raw_text) if proc.raw_text else 0
    is_ocr = proc.extraction_method in [ExtractionMethod.OCR, ExtractionMethod.HYBRID]
    
    if proc.extraction_method == ExtractionMethod.DIGITAL_PDF:
        quality_label = "Digital PDF (Text Extracted)"
    elif proc.extraction_method == ExtractionMethod.HYBRID:
        quality_label = "Hybrid Document (Digital + OCR Extracted)"
    elif proc.extraction_method == ExtractionMethod.OCR:
        quality_label = "Scanned Document (OCR Extracted)"
    elif proc.processing_stage == ProcessingStage.OCR:
        quality_label = "Scanned Document (OCR Required)"
    else:
        quality_label = "Pending Processing"

    # Determine confidence level
    conf = proc.classification_confidence or 0.0
    if conf >= 0.80:
        conf_level = ClassificationConfidenceLevel.HIGH
    elif conf >= 0.55:
        conf_level = ClassificationConfidenceLevel.MEDIUM
    elif conf > 0.0:
        conf_level = ClassificationConfidenceLevel.LOW
    else:
        conf_level = None

    return DocumentExtractedTextResponse(
        document_id=doc.id,
        bid_id=bid.id,
        processing_status=proc.processing_status,
        processing_stage=proc.processing_stage,
        extraction_method=proc.extraction_method,
        page_count=proc.page_count,
        character_count=char_count,
        raw_text=proc.raw_text,
        normalized_text=proc.normalized_text,
        is_ocr_required=is_ocr or proc.processing_stage == ProcessingStage.OCR,
        quality_label=quality_label,
        # Classification summary
        detected_document_type=proc.detected_document_type,
        classification_confidence=proc.classification_confidence,
        classification_confidence_level=conf_level,
        classification_reason=proc.classification_reason,
        classification_requires_review=proc.classification_requires_review,
        # Part 4E: Structured Extraction summary
        extracted_data=proc.extracted_data,
        extraction_confidence=proc.extraction_confidence,
        extraction_requires_review=proc.extraction_requires_review,
    )


def get_document_classification(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DocumentClassificationResponse:
    """
    Retrieves the document classification details and explainability metrics for a document.
    Enforces strict tenant isolation.
    """
    _, bid, doc = _get_document_for_bidder(db, current_user, bid_id, document_id)

    proc = doc.processing or create_or_get_processing_record(db, doc.id)

    conf = proc.classification_confidence or 0.0
    if conf >= 0.80:
        conf_level = ClassificationConfidenceLevel.HIGH
    elif conf >= 0.55:
        conf_level = ClassificationConfidenceLevel.MEDIUM
    else:
        conf_level = ClassificationConfidenceLevel.LOW

    expected_type = derive_expected_document_type(doc.tender_requirement, doc.document_type)

    return DocumentClassificationResponse(
        document_id=doc.id,
        bid_id=bid.id,
        processing_status=proc.processing_status,
        processing_stage=proc.processing_stage,
        detected_document_type=proc.detected_document_type or DocumentClass.UNKNOWN,
        expected_document_type=expected_type,
        classification_confidence=conf,
        confidence_level=conf_level,
        classification_method=proc.classification_method or "RULE_BASED",
        classification_reason=proc.classification_reason or "Pending classification",
        classification_requires_review=proc.classification_requires_review,
    )


def execute_structured_extraction(
    db: Session,
    document_processing: DocumentProcessing,
    bid_document: BidDocument,
) -> DocumentProcessing:
    """
    Executes deterministic structured entity extraction based on the detected document class.
    Populates extracted_data JSON, extraction_confidence, extraction_requires_review,
    and structured_extraction_method.
    """
    text_to_parse = document_processing.normalized_text or document_processing.raw_text or ""
    doc_type = document_processing.detected_document_type or DocumentClass.UNKNOWN

    res = extract_structured_entities_from_text(
        text=text_to_parse,
        document_type=doc_type,
        original_filename=bid_document.original_filename,
    )

    document_processing.extracted_data = res.to_dict()
    document_processing.extraction_confidence = res.overall_confidence
    document_processing.extraction_requires_review = res.requires_review
    document_processing.structured_extraction_method = res.extraction_method

    db.commit()
    db.refresh(document_processing)
    return document_processing


def get_document_extracted_data(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DocumentExtractedDataResponse:
    """
    Retrieves the authenticated bidder's extracted structured entity data,
    field-level confidence, evidence snippets, page provenance, and review flags.
    Enforces strict tenant isolation.
    """
    _, bid, doc = _get_document_for_bidder(db, current_user, bid_id, document_id)

    proc = doc.processing or create_or_get_processing_record(db, doc.id)

    # Convert stored JSON into dict of ExtractedFieldItem
    raw_fields = proc.extracted_data.get("fields", {}) if proc.extracted_data and isinstance(proc.extracted_data, dict) else {}
    fields_dict: Dict[str, ExtractedFieldItem] = {}
    for k, v in raw_fields.items():
        if isinstance(v, dict):
            fields_dict[k] = ExtractedFieldItem(
                value=v.get("value"),
                confidence=v.get("confidence", 1.0),
                evidence=v.get("evidence", ""),
                page=v.get("page", 1),
                is_conflict=v.get("is_conflict", False),
                conflict_values=v.get("conflict_values", []),
            )

    conf = proc.extraction_confidence or 0.0
    if conf >= 0.80:
        conf_level = ClassificationConfidenceLevel.HIGH
    elif conf >= 0.55:
        conf_level = ClassificationConfidenceLevel.MEDIUM
    else:
        conf_level = ClassificationConfidenceLevel.LOW

    review_reasons = proc.extracted_data.get("review_reasons", []) if proc.extracted_data and isinstance(proc.extracted_data, dict) else []

    return DocumentExtractedDataResponse(
        document_id=doc.id,
        bid_id=bid.id,
        document_type=proc.detected_document_type or DocumentClass.UNKNOWN,
        fields=fields_dict,
        extraction_confidence=conf,
        confidence_level=conf_level,
        extraction_method=proc.structured_extraction_method or "RULE_BASED",
        requires_review=proc.extraction_requires_review,
        review_reasons=review_reasons,
    )


# ---------------------------------------------------------------------------
# Internal Pipeline Helper Functions
# ---------------------------------------------------------------------------

def mark_processing_started(
    db: Session,
    processing_id: uuid.UUID,
    stage: str = ProcessingStage.TEXT_EXTRACTION,
) -> DocumentProcessing:
    """Marks processing record as PROCESSING with started_at timestamp."""
    proc = db.scalars(select(DocumentProcessing).where(DocumentProcessing.id == processing_id)).one()
    proc.processing_status = ProcessingStatus.PROCESSING
    proc.processing_stage = stage
    proc.processing_started_at = datetime.now(timezone.utc)
    proc.error_code = None
    proc.error_message = None
    db.commit()
    db.refresh(proc)
    return proc


def update_processing_stage(
    db: Session,
    processing_id: uuid.UUID,
    stage: str,
    extraction_method: Optional[str] = None,
) -> DocumentProcessing:
    """Updates the execution stage and extraction method of an ongoing processing job."""
    proc = db.scalars(select(DocumentProcessing).where(DocumentProcessing.id == processing_id)).one()
    proc.processing_stage = stage
    if extraction_method:
        proc.extraction_method = extraction_method
    db.commit()
    db.refresh(proc)
    return proc


def mark_processing_completed(
    db: Session,
    processing_id: uuid.UUID,
    page_count: Optional[int] = None,
    raw_text: Optional[str] = None,
    normalized_text: Optional[str] = None,
) -> DocumentProcessing:
    """Marks processing as COMPLETED with completion timestamp and telemetry."""
    proc = db.scalars(select(DocumentProcessing).where(DocumentProcessing.id == processing_id)).one()
    proc.processing_status = ProcessingStatus.COMPLETED
    proc.processing_stage = ProcessingStage.COMPLETED
    proc.processing_completed_at = datetime.now(timezone.utc)
    if page_count is not None:
        proc.page_count = page_count
    if raw_text is not None:
        proc.raw_text = raw_text
    if normalized_text is not None:
        proc.normalized_text = normalized_text
    proc.error_code = None
    proc.error_message = None
    db.commit()
    db.refresh(proc)
    return proc


def mark_processing_failed(
    db: Session,
    processing_id: uuid.UUID,
    error_code: str,
    error_message: str,
) -> DocumentProcessing:
    """Marks processing as FAILED with error code and sanitized description."""
    proc = db.scalars(select(DocumentProcessing).where(DocumentProcessing.id == processing_id)).one()
    proc.processing_status = ProcessingStatus.FAILED
    proc.processing_completed_at = datetime.now(timezone.utc)
    proc.error_code = error_code
    proc.error_message = error_message
    db.commit()
    db.refresh(proc)
    return proc


def backfill_missing_processing_records(db: Session) -> int:
    """
    Idempotently provisions QUEUED processing records for all existing BidDocument
    records that do not currently have a corresponding DocumentProcessing record.
    """
    subquery = select(DocumentProcessing.bid_document_id)
    missing_docs = db.scalars(
        select(BidDocument).where(BidDocument.id.not_in(subquery))
    ).all()

    created_count = 0
    for doc in missing_docs:
        record = DocumentProcessing(
            id=uuid.uuid4(),
            bid_document_id=doc.id,
            processing_status=ProcessingStatus.QUEUED,
            processing_stage=ProcessingStage.INGESTION,
            extraction_method=ExtractionMethod.NONE,
        )
        db.add(record)
        created_count += 1

    if created_count > 0:
        db.commit()

    return created_count
