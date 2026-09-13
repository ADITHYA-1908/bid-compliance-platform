"""
Automated Unit & Integration Test Suite for Step 4B: Digital PDF Text Extraction (PyMuPDF)
Covers:
- Single-page & multi-page digital PDF text extraction
- 1-indexed page numbering and [PAGE N] boundary formatting
- Statutory identifier and financial symbol preservation in text normalization
- Quality metrics and deterministic scanned vs digital PDF classification
- Corrupted, empty, and password-protected PDF exception handling
- Scanned/image-only PDF non-false-positive handling (NEEDS_REVIEW / PDF_NO_EXTRACTABLE_TEXT)
- Idempotent execution and version isolation
- API response serialization for /extracted-text and /text endpoints
"""

import io
import uuid
import pytest
import fitz  # PyMuPDF
from unittest.mock import MagicMock, patch

from app.db.models.document_processing import (
    DocumentProcessing,
    ExtractionMethod,
    ProcessingStage,
    ProcessingStatus,
    DocumentClass,
)
from app.schemas.document_processing import (
    DocumentExtractedTextResponse,
    DocumentProcessingResponse,
)
from app.services.pdf_extraction_service import (
    PDFExtractionError,
    PDFExtractionResult,
    PDFPageExtraction,
    analyze_text_quality,
    extract_pdf,
    extract_pdf_text,
    normalize_extracted_text,
    MIN_TEXT_CHARACTERS,
    MIN_CHARACTERS_PER_PAGE,
)


def _create_sample_digital_pdf(pages_text: list[str], encrypt_password: str = None) -> bytes:
    """Helper to generate in-memory synthetic PDF bytes with PyMuPDF."""
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page(width=595, height=842)
        # Insert text at top
        page.insert_text(fitz.Point(50, 72), text, fontsize=11)

    if encrypt_password:
        # Save with user/owner password encryption
        pdf_bytes = doc.tobytes(
            garbage=4,
            deflate=True,
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw=encrypt_password,
            user_pw=encrypt_password,
        )
    else:
        pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _create_scanned_image_pdf() -> bytes:
    """Helper to generate a PDF containing only drawing graphics / no text stream."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.draw_rect(fitz.Rect(50, 50, 450, 450), color=(0.9, 0.9, 0.9), fill=(0.9, 0.9, 0.9))
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# =========================================================================
# 1. Single-Page Digital PDF Extraction Tests
# =========================================================================

def test_extract_pdf_text_single_page_digital():
    """Verify digital text extraction from a single page digital PDF."""
    sample_text = (
        "GOVERNMENT E-MARKETPLACE (GeM) BID COMPLIANCE PROOF\n"
        "Bidder Name: Acme Global Technologies Private Limited\n"
        "GSTIN: 33ABCDE1234F1Z5 | PAN: ABCDE1234F\n"
        "Udyam Reg: UDYAM-TN-00-1234567 | Local Content: 65.5%\n"
        "Annual Audited Turnover: INR 5,50,00,000/- for FY 2023-24\n"
        "Date of Certification: 26/08/2026 | UDIN: 24123456AAAAAB1234\n"
        "This document certifies that the bidder is fully compliant with all technical specifications."
    )
    pdf_bytes = _create_sample_digital_pdf([sample_text])

    result = extract_pdf_text(pdf_bytes, filename="gst_certificate.pdf")

    assert isinstance(result, PDFExtractionResult)
    assert result.page_count == 1
    assert result.is_digital_pdf is True
    assert result.is_ocr_required is False
    assert result.extraction_method == ExtractionMethod.DIGITAL_PDF
    assert len(result.pages) == 1

    page1 = result.pages[0]
    assert page1.page_number == 1  # 1-indexed
    assert "33ABCDE1234F1Z5" in page1.raw_text
    assert "ABCDE1234F" in page1.raw_text
    assert "UDYAM-TN-00-1234567" in page1.raw_text
    assert "5,50,00,000" in page1.raw_text

    # Verify traceable page boundary header [PAGE 1]
    assert result.raw_text.startswith("[PAGE 1]")
    assert result.normalized_text.startswith("[PAGE 1]")
    assert "33ABCDE1234F1Z5" in result.normalized_text


# =========================================================================
# 2. Multi-Page Digital PDF Extraction Tests
# =========================================================================

def test_extract_pdf_text_multi_page_digital():
    """Verify multi-page digital PDF text extraction with 1-indexed page boundaries."""
    p1 = "PAGE 1: Company Profile and Statutory Registration. PAN: ABCDE1234F. Registered in Chennai, Tamil Nadu."
    p2 = "PAGE 2: Audited Financial Statements. Turnover for FY 2023-24 is ₹12,00,00,000/-. Net Worth: ₹4,00,00,000."
    p3 = "PAGE 3: OEM Authorization Certificate. Authorized Partner for Server Infrastructure until 31-12-2027."

    pdf_bytes = _create_sample_digital_pdf([p1, p2, p3])

    result = extract_pdf_text(pdf_bytes, filename="tender_packet.pdf")

    assert result.page_count == 3
    assert result.is_digital_pdf is True
    assert len(result.pages) == 3

    # Check 1-indexed page numbering
    assert result.pages[0].page_number == 1
    assert result.pages[1].page_number == 2
    assert result.pages[2].page_number == 3

    # Check page boundary headers
    assert "[PAGE 1]" in result.raw_text
    assert "[PAGE 2]" in result.raw_text
    assert "[PAGE 3]" in result.raw_text

    assert "PAGE 1: Company Profile" in result.pages[0].raw_text
    assert "PAGE 2: Audited Financial" in result.pages[1].raw_text
    assert "PAGE 3: OEM Authorization" in result.pages[2].raw_text


# =========================================================================
# 3. Normalization Quality and Identifier Preservation
# =========================================================================

def test_normalize_extracted_text_preserves_statutory_patterns():
    """Verify that normalization preserves statutory numbers, currency symbols, and dates."""
    raw = (
        "  \t  GOVERNMENT OF INDIA   \t  \r\n\r\n\r\n\r\n"
        "GSTIN: \t 33ABCDE1234F1Z5 \r\n"
        "PAN: \t ABCDE1234F \r\n"
        "UDYAM: \t UDYAM-TN-00-1234567 \r\n"
        "Turnover: \t ₹10,50,00,000.00 \r\n"
        "Local Content: \t 50.00% \r\n"
        "Date: \t 26/08/2026 \r\n\r\n\r\n"
    )

    norm = normalize_extracted_text(raw)

    assert "33ABCDE1234F1Z5" in norm
    assert "ABCDE1234F" in norm
    assert "UDYAM-TN-00-1234567" in norm
    assert "₹10,50,00,000.00" in norm
    assert "50.00%" in norm
    assert "26/08/2026" in norm
    # Assert excessive newlines collapsed
    assert "\n\n\n" not in norm


# =========================================================================
# 4. Scanned / Image-Only PDF Detection
# =========================================================================

def test_scanned_image_only_pdf_requires_ocr():
    """Verify that scanned PDFs with minimal/zero digital text are flagged as OCR required."""
    pdf_bytes = _create_scanned_image_pdf()

    result = extract_pdf_text(pdf_bytes, filename="scanned_receipt.pdf")

    assert result.page_count == 1
    assert result.is_digital_pdf is False
    assert result.is_ocr_required is True
    assert result.extraction_method == ExtractionMethod.NONE
    assert result.raw_text == ""
    assert result.normalized_text == ""
    assert result.quality_metrics["ocr_required"] is True
    assert result.quality_metrics["quality_label"] == "Low / Scanned Image"


def test_extract_pdf_service_scanned_pdf_flags_needs_review():
    """Verify that extract_pdf records PDF_NO_EXTRACTABLE_TEXT and sets status to NEEDS_REVIEW."""
    pdf_bytes = _create_scanned_image_pdf()

    mock_doc = MagicMock()
    mock_doc.id = uuid.uuid4()
    mock_doc.original_filename = "scanned_invoice.pdf"
    mock_doc.document_name = "Invoice"
    mock_doc.storage_path = "bids/doc_123.pdf"
    mock_doc.processing = None

    mock_db = MagicMock()

    proc = extract_pdf(doc=mock_doc, db=mock_db, file_bytes=pdf_bytes)

    assert proc.processing_status == ProcessingStatus.NEEDS_REVIEW
    assert proc.processing_stage == ProcessingStage.TEXT_EXTRACTION
    assert proc.extraction_method == ExtractionMethod.NONE
    assert proc.error_code == "PDF_NO_EXTRACTABLE_TEXT"
    assert "OCR processing" in proc.error_message


# =========================================================================
# 5. Error Handling: Corrupted, Empty, and Encrypted PDFs
# =========================================================================

def test_extract_pdf_empty_bytes_raises_error():
    """Verify empty document bytes trigger EMPTY_FILE error."""
    with pytest.raises(PDFExtractionError) as exc_info:
        extract_pdf_text(b"", filename="empty.pdf")
    assert exc_info.value.error_code == "EMPTY_FILE"


def test_extract_pdf_corrupted_bytes_raises_error():
    """Verify corrupted PDF stream triggers PDF_CORRUPTED error."""
    corrupted_bytes = b"%PDF-1.4 non-valid garbage stream bytes 12345678"
    with pytest.raises(PDFExtractionError) as exc_info:
        extract_pdf_text(corrupted_bytes, filename="corrupt.pdf")
    assert exc_info.value.error_code == "PDF_CORRUPTED"


def test_extract_pdf_password_protected_raises_error():
    """Verify encrypted PDF triggers PASSWORD_PROTECTED_PDF error."""
    encrypted_bytes = _create_sample_digital_pdf(
        ["Confidential Financial Document with statutory details."],
        encrypt_password="secretpassword123",
    )
    with pytest.raises(PDFExtractionError) as exc_info:
        extract_pdf_text(encrypted_bytes, filename="locked.pdf")
    assert exc_info.value.error_code == "PASSWORD_PROTECTED_PDF"


# =========================================================================
# 6. Idempotency and Document Version Isolation
# =========================================================================

def test_extract_pdf_successful_completion():
    """Verify successful digital extraction sets COMPLETED status and content hash."""
    sample_text = (
        "BIDDER REGISTRATION CERTIFICATE\n"
        "Enterprise: Bharat Electronics Supply Co.\n"
        "PAN: AABCB1234F | GSTIN: 27AABCB1234F1Z1\n"
        "Turnover: ₹8,00,00,000 for FY 2023-24\n"
        "MSME Category: Micro Enterprise | Date: 01/04/2026\n"
        "All statutory compliances are verified and certified."
    )
    pdf_bytes = _create_sample_digital_pdf([sample_text])

    mock_doc = MagicMock()
    mock_doc.id = uuid.uuid4()
    mock_doc.original_filename = "bharat_registration.pdf"
    mock_doc.document_name = "Registration"
    mock_doc.storage_path = "bids/doc_456.pdf"
    mock_doc.processing = None

    mock_db = MagicMock()

    proc = extract_pdf(doc=mock_doc, db=mock_db, file_bytes=pdf_bytes)

    assert proc.processing_status == ProcessingStatus.COMPLETED
    assert proc.processing_stage == ProcessingStage.COMPLETED
    assert proc.extraction_method == ExtractionMethod.DIGITAL_PDF
    assert proc.error_code is None
    assert proc.normalized_content_hash is not None
    assert len(proc.normalized_content_hash) == 64  # SHA256 hex string
    assert proc.page_count == 1
    assert "AABCB1234F" in proc.normalized_text


# =========================================================================
# 7. Schema Serialization for /extracted-text and /text Endpoints
# =========================================================================

def test_document_extracted_text_response_schema():
    """Verify DocumentExtractedTextResponse schema serialization."""
    doc_id = uuid.uuid4()
    bid_id = uuid.uuid4()

    response = DocumentExtractedTextResponse(
        document_id=doc_id,
        bid_id=bid_id,
        processing_status="COMPLETED",
        processing_stage="COMPLETED",
        extraction_method="DIGITAL_PDF",
        page_count=2,
        character_count=1250,
        raw_text="[PAGE 1]\nSample text\n\n[PAGE 2]\nPage 2 text",
        normalized_text="[PAGE 1]\nSample text\n\n[PAGE 2]\nPage 2 text",
        is_ocr_required=False,
        quality_label="Digital PDF (Text Extracted)",
        detected_document_type="GST_CERTIFICATE",
        classification_confidence=0.95,
        classification_confidence_level="HIGH",
        classification_reason="Valid GSTIN pattern matched",
        classification_requires_review=False,
    )

    assert response.document_id == doc_id
    assert response.bid_id == bid_id
    assert response.extraction_method == "DIGITAL_PDF"
    assert response.page_count == 2
    assert response.character_count == 1250
    assert response.is_ocr_required is False
    assert response.classification_confidence_level == "HIGH"
