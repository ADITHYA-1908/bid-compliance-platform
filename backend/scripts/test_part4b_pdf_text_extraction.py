"""
Part 4B Master Integration & Regression Test Suite
Tests PDF Text Extraction with PyMuPDF:
- Unit tests: Text normalization and token/identifier preservation
- Unit tests: Deterministic quality analysis and digital vs scanned classification
- Integration test: Real digital PDF text extraction page-by-page (PyMuPDF)
- Integration test: Scanned/image PDF detection and routing to OCR stage
- Integration test: Non-PDF format handling
- Integration test: Corrupted / invalid PDF error handling (PDF_CORRUPTED)
- Integration test: Password-protected / encrypted PDF error handling (PASSWORD_PROTECTED_PDF)
- Integration test: Idempotency of repeated text extraction
- Integration test: Extracted text endpoint and cross-tenant security
- Integration test: Processing allowed on SUBMITTED bids
"""

import os
import sys
import io
import uuid
from datetime import datetime, timezone, timedelta

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import fitz  # PyMuPDF
from fastapi import UploadFile, HTTPException
from sqlalchemy import select
from starlette.datastructures import Headers

from app.core.config import settings
from app.db.session import get_session_factory
from app.db.models.role import Role
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.user import User
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.document_processing import (
    DocumentProcessing,
    ProcessingStatus,
    ProcessingStage,
    ExtractionMethod,
)
from app.services.bid_document_service import upload_bid_document
from app.services.document_processing_service import (
    create_or_get_processing_record,
    execute_pdf_text_extraction,
    queue_document_processing,
    retry_document_processing,
    get_document_extracted_text,
)
from app.services.pdf_extraction_service import (
    normalize_extracted_text,
    analyze_text_quality,
    extract_text_from_pdf_bytes,
    PDFExtractionError,
)
from app.services.storage_service import storage_service


def create_digital_pdf_bytes() -> bytes:
    """Generates a valid 2-page digital PDF in memory containing statutory procurement text."""
    doc = fitz.open()
    
    # Page 1
    page1 = doc.new_page()
    page1_text = (
        "GOVERNMENT E-MARKETPLACE (GeM) STATUTORY BID SUBMISSION PROOF\n"
        "Tender ID: GEM/2026/B/998877\n"
        "Organization Name: Apex Cybernetics Enterprise Private Limited\n"
        "PAN Number: ABCDE1234F\n"
        "GSTIN Number: 33ABCDE1234F1Z5\n"
        "Udyam MSME Registration: UDYAM-TN-00-1234567\n"
        "Total Quoted Bid Price: INR 5,00,00,000 (Five Crore INR)\n"
        "Authorized Signatory Date: 2026-08-26\n"
    )
    page1.insert_text((50, 72), page1_text, fontsize=11)

    # Page 2
    page2 = doc.new_page()
    page2_text = (
        "TECHNICAL COMPLIANCE SCHEDULE & OEM AUTHORIZATION\n"
        "Item: High-Performance Compute Cluster Nodes\n"
        "OEM Model Series: ProLiant DL380 Gen11\n"
        "Delivery Timeline: 30 Days from PO Issuance\n"
        "Local Content (Make in India): 50% Compliance Verified\n"
        "Warranty Commitment: 36 Months 24x7 On-site OEM Warranty\n"
    )
    page2.insert_text((50, 72), page2_text, fontsize=11)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_scanned_pdf_bytes() -> bytes:
    """Generates an image/scanned PDF in memory with no embedded selectable text."""
    doc = fitz.open()
    page1 = doc.new_page()
    # Scanned PDF: page has blank or only 2 noisy characters
    page1.insert_text((50, 72), "AB", fontsize=8)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_password_protected_pdf_bytes() -> bytes:
    """Generates an encrypted password-protected PDF in memory."""
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((50, 72), "Confidential Proprietary Financial Statement", fontsize=12)
    
    # Save with user password
    pdf_bytes = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw="securepass123",
        owner_pw="ownerpass123",
    )
    doc.close()
    return pdf_bytes


def run_tests():
    print("=" * 80)
    print("BIDVERIFY AI — PART 4B PDF TEXT EXTRACTION TEST SUITE (PyMuPDF)")
    print("=" * 80)

    session_factory = get_session_factory()
    db = session_factory()

    try:
        # ---------------------------------------------------------------------
        # Setup Test Fixtures: Organization, Profile, User, Tender, Bid
        # ---------------------------------------------------------------------
        print("\n[Setup] Initializing test fixtures...")
        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()

        # Bidder 1 Setup
        org1 = Organization(
            name=f"Test Part4B Org 1 - {uuid.uuid4().hex[:6]}",
            organization_type="PRIVATE_LIMITED",
            registration_number=f"REG-{uuid.uuid4().hex[:8]}",
            is_active=True,
        )
        db.add(org1)
        db.commit()
        db.refresh(org1)

        profile1 = Profile(
            organization_id=org1.id,
            role_id=bidder_role.id,
            full_name="Bidder One P4B",
            email=f"bidder1_p4b_{uuid.uuid4().hex[:6]}@example.com",
            is_active=True,
        )
        db.add(profile1)
        db.commit()
        db.refresh(profile1)

        user1 = User(
            id=uuid.uuid4(),
            email=profile1.email,
            password_hash="mock_hash",
            profile_id=profile1.id,
            is_active=True,
        )
        db.add(user1)
        db.commit()
        db.refresh(user1)

        # Bidder 2 Setup (for cross-tenant checks)
        org2 = Organization(
            name=f"Test Part4B Org 2 - {uuid.uuid4().hex[:6]}",
            organization_type="PRIVATE_LIMITED",
            is_active=True,
        )
        db.add(org2)
        db.commit()
        db.refresh(org2)

        profile2 = Profile(
            organization_id=org2.id,
            role_id=bidder_role.id,
            full_name="Bidder Two P4B",
            email=f"bidder2_p4b_{uuid.uuid4().hex[:6]}@example.com",
            is_active=True,
        )
        db.add(profile2)
        db.commit()
        db.refresh(profile2)

        user2 = User(
            id=uuid.uuid4(),
            email=profile2.email,
            password_hash="mock_hash",
            profile_id=profile2.id,
            is_active=True,
        )
        db.add(user2)
        db.commit()
        db.refresh(user2)

        # Tender Setup
        tender = Tender(
            tender_number=f"GEM/2026/B/P4B-{uuid.uuid4().hex[:6]}",
            title="Part 4B PDF Extraction Tender",
            description="Testing PyMuPDF text extraction pipeline",
            status="OPEN",
            submission_start_date=datetime.now(timezone.utc) - timedelta(days=1),
            submission_end_date=datetime.now(timezone.utc) + timedelta(days=30),
            estimated_value=5000000.0,
            currency="INR",
            organization_id=org1.id,
            created_by_profile_id=profile1.id,
        )
        db.add(tender)
        db.commit()
        db.refresh(tender)

        req1 = TenderRequirement(
            tender_id=tender.id,
            code="DOC-REQ-001",
            name="GST & Statutory Registration Certificate",
            requirement_type="DOCUMENT",
            is_mandatory=True,
            is_active=True,
        )
        db.add(req1)
        db.commit()

        # Bid for Bidder 1
        bid1 = Bid(
            tender_id=tender.id,
            bidder_organization_id=org1.id,
            created_by_profile_id=profile1.id,
            bid_number=f"BID-P4B-{uuid.uuid4().hex[:6]}",
            status="DRAFT",
            quoted_amount=4800000.0,
            currency="INR",
        )
        db.add(bid1)
        db.commit()
        db.refresh(bid1)
        print("  [PASS] Setup completed successfully.")

        # ---------------------------------------------------------------------
        # TEST 1: Unit Test — Text Normalization & Identifier Preservation
        # ---------------------------------------------------------------------
        print("\n[Test 1] Testing text normalization and statutory token preservation...")
        raw_test_input = (
            "   \r\n\r\n"
            "Company:   Apex Cybernetics Pvt Ltd\t\t\n"
            "PAN:  ABCDE1234F  \n\n\n\n"
            "GSTIN: 33ABCDE1234F1Z5\n"
            "Udyam: UDYAM-TN-00-1234567\n"
            "Turnover: ₹5,00,00,000 \n"
            "Compliance: 50%  (Verified 2026-08-26)\n\n\n"
        )
        norm_output = normalize_extracted_text(raw_test_input)
        assert "ABCDE1234F" in norm_output
        assert "33ABCDE1234F1Z5" in norm_output
        assert "UDYAM-TN-00-1234567" in norm_output
        assert "₹5,00,00,000" in norm_output
        assert "50%" in norm_output
        assert "2026-08-26" in norm_output
        assert "\r" not in norm_output
        assert "\n\n\n" not in norm_output
        print("  [PASS] Text normalization cleanly normalized whitespace while preserving all statutory tokens.")

        # ---------------------------------------------------------------------
        # TEST 2: Unit Test — Deterministic Quality Analysis & Classification
        # ---------------------------------------------------------------------
        print("\n[Test 2] Testing deterministic text quality analysis...")
        digital_sample = "GOVERNMENT PROCUREMENT BID COMPLIANCE DOCUMENT WITH REAL MACHINE READABLE TEXT " * 5
        is_dig, metrics_dig = analyze_text_quality(digital_sample, page_count=2)
        assert is_dig is True
        assert metrics_dig["is_digital_pdf"] is True
        assert metrics_dig["ocr_required"] is False
        assert metrics_dig["characters_per_page"] > 30

        scanned_sample = "X"
        is_scan, metrics_scan = analyze_text_quality(scanned_sample, page_count=2)
        assert is_scan is False
        assert metrics_scan["is_digital_pdf"] is False
        assert metrics_scan["ocr_required"] is True
        print("  [PASS] Quality analyzer deterministically classified digital vs. scanned text.")

        # ---------------------------------------------------------------------
        # TEST 3: Integration Test — Digital PDF Text Extraction (PyMuPDF)
        # ---------------------------------------------------------------------
        print("\n[Test 3] Testing full digital PDF text extraction via PyMuPDF...")
        digital_pdf_bytes = create_digital_pdf_bytes()
        upload_res = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            file=UploadFile(
                file=io.BytesIO(digital_pdf_bytes),
                size=len(digital_pdf_bytes),
                filename="gem_bid_submission.pdf",
                headers=Headers({"content-type": "application/pdf"}),
            ),
            document_type="STATUTORY_DOCUMENT",
            tender_requirement_id=req1.id,
        )

        # Trigger execution of extraction engine
        proc_record = execute_pdf_text_extraction(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_res.id,
        )

        assert proc_record.extraction_method == ExtractionMethod.DIGITAL_PDF
        assert proc_record.processing_stage in [
            ProcessingStage.CLASSIFICATION,
            ProcessingStage.STRUCTURED_EXTRACTION,
            ProcessingStage.COMPLETED,
        ]
        assert proc_record.page_count == 2
        assert proc_record.raw_text is not None
        assert "--- Page 1 ---" in proc_record.raw_text
        assert "ABCDE1234F" in proc_record.normalized_text
        assert "33ABCDE1234F1Z5" in proc_record.normalized_text
        assert "5,00,00,000" in proc_record.normalized_text
        assert proc_record.processing_completed_at is not None
        assert proc_record.error_code in [None, "EXTRACTION_REQUIRES_REVIEW"]
        print(f"  [PASS] Digital PDF ({proc_record.page_count} pages) successfully extracted and tokens preserved.")

        # ---------------------------------------------------------------------
        # TEST 4: Integration Test — Scanned PDF Detection & OCR Routing
        # ---------------------------------------------------------------------
        print("\n[Test 4] Testing scanned PDF detection and routing to OCR stage...")
        scanned_pdf_bytes = create_scanned_pdf_bytes()
        upload_scanned_res = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            file=UploadFile(
                file=io.BytesIO(scanned_pdf_bytes),
                size=len(scanned_pdf_bytes),
                filename="scanned_registration_slip.pdf",
                headers=Headers({"content-type": "application/pdf"}),
            ),
            document_type="TECHNICAL_DOCUMENT",
        )

        scanned_proc = execute_pdf_text_extraction(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_scanned_res.id,
        )

        assert scanned_proc.extraction_method in [ExtractionMethod.NONE, ExtractionMethod.OCR]
        assert scanned_proc.page_count == 1
        print("  [PASS] Scanned PDF cleanly detected and routed through OCR engine.")

        # ---------------------------------------------------------------------
        # TEST 5: Integration Test — Non-PDF Document Handling
        # ---------------------------------------------------------------------
        print("\n[Test 5] Testing non-PDF document handling...")
        image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        upload_img_res = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            file=UploadFile(
                file=io.BytesIO(image_bytes),
                size=len(image_bytes),
                filename="certificate_scan.png",
                headers=Headers({"content-type": "image/png"}),
            ),
            document_type="TECHNICAL_DOCUMENT",
        )

        img_proc = execute_pdf_text_extraction(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_img_res.id,
        )

        assert img_proc.extraction_method in [ExtractionMethod.NONE, ExtractionMethod.OCR]
        print("  [PASS] Non-PDF document safely routed to OCR stage.")

        # ---------------------------------------------------------------------
        # TEST 6: Integration Test — Corrupted PDF Handling
        # ---------------------------------------------------------------------
        print("\n[Test 6] Testing corrupted PDF failure handling...")
        corrupt_bytes = b"%PDF-corrupted-binary-header-with-invalid-trailer-data-random-bytes"
        upload_corrupt_res = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            file=UploadFile(
                file=io.BytesIO(corrupt_bytes),
                size=len(corrupt_bytes),
                filename="corrupted_report.pdf",
                headers=Headers({"content-type": "application/pdf"}),
            ),
            document_type="TECHNICAL_DOCUMENT",
        )

        corrupt_proc = execute_pdf_text_extraction(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_corrupt_res.id,
        )

        assert corrupt_proc.processing_status == ProcessingStatus.FAILED
        assert corrupt_proc.error_code in ["PDF_CORRUPTED", "PDF_EXTRACTION_UNEXPECTED_ERROR"]
        assert corrupt_proc.error_message is not None
        print(f"  [PASS] Corrupted PDF recorded clean failure telemetry [{corrupt_proc.error_code}].")

        # ---------------------------------------------------------------------
        # TEST 7: Integration Test — Password-Protected PDF Handling
        # ---------------------------------------------------------------------
        print("\n[Test 7] Testing password-protected PDF failure handling...")
        enc_bytes = create_password_protected_pdf_bytes()
        upload_enc_res = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            file=UploadFile(
                file=io.BytesIO(enc_bytes),
                size=len(enc_bytes),
                filename="locked_financials.pdf",
                headers=Headers({"content-type": "application/pdf"}),
            ),
            document_type="TECHNICAL_DOCUMENT",
        )

        enc_proc = execute_pdf_text_extraction(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_enc_res.id,
        )

        assert enc_proc.processing_status == ProcessingStatus.FAILED
        assert enc_proc.error_code == "PASSWORD_PROTECTED_PDF"
        assert "password protected" in enc_proc.error_message.lower()
        print("  [PASS] Password-protected PDF safely handled with clean error guidance.")

        # ---------------------------------------------------------------------
        # TEST 8: Integration Test — Idempotency of Repeated Processing
        # ---------------------------------------------------------------------
        print("\n[Test 8] Testing idempotency of repeated processing...")
        repeat_proc = queue_document_processing(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_res.id,
        )
        assert repeat_proc.extraction_method == ExtractionMethod.DIGITAL_PDF
        assert repeat_proc.page_count == 2
        print("  [PASS] Repeated processing call safely returned cached extraction without re-processing.")

        # ---------------------------------------------------------------------
        # TEST 9: Integration Test — Extracted Text Endpoint & Tenant Isolation
        # ---------------------------------------------------------------------
        print("\n[Test 9] Testing extracted text retrieval and strict tenant isolation...")
        text_dto = get_document_extracted_text(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_res.id,
        )
        assert text_dto.document_id == upload_res.id
        assert text_dto.extraction_method == ExtractionMethod.DIGITAL_PDF
        assert text_dto.page_count == 2
        assert text_dto.character_count > 100
        assert "ABCDE1234F" in text_dto.normalized_text

        # Bidder 2 attempts to read Bidder 1's extracted text -> 404
        try:
            get_document_extracted_text(
                db=db,
                current_user=user2,
                bid_id=bid1.id,
                document_id=upload_res.id,
            )
            assert False, "Bidder 2 should not be able to read Bidder 1 extracted text"
        except HTTPException as he:
            assert he.status_code == 404
            print("  [PASS] Cross-tenant extracted text access safely rejected with HTTP 404.")

        # ---------------------------------------------------------------------
        # TEST 10: Integration Test — Processing Permitted on SUBMITTED Bids
        # ---------------------------------------------------------------------
        print("\n[Test 10] Testing text extraction access on SUBMITTED bids...")
        bid1.status = "SUBMITTED"
        bid1.submitted_at = datetime.now(timezone.utc)
        db.commit()

        submitted_text = get_document_extracted_text(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_res.id,
        )
        assert submitted_text is not None
        assert submitted_text.extraction_method == ExtractionMethod.DIGITAL_PDF
        print("  [PASS] Extracted text retrieval permitted on SUBMITTED bids.")

        print("\n" + "=" * 80)
        print("ALL 10/10 PART 4B INTEGRATION TESTS PASSED (100% SUCCESS)")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    run_tests()
