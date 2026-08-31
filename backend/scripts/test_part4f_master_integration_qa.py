"""
Part 4F Master Integration, Confidence Review, Hardening & QA Test Suite
BidVerify AI — GeM Document Processing & Extraction Engine

Tests:
1. End-to-End Digital PDF Flow (PyMuPDF -> Normalization -> Classification -> Structured Extraction)
2. End-to-End Scanned PDF Flow (OpenCV + PaddleOCR fallback)
3. End-to-End Standalone Image Flow (PNG/JPG -> Preprocessing -> OCR)
4. End-to-End Hybrid PDF Flow (Page 1 PyMuPDF + Page 2 OCR -> method HYBRID)
5. Ambiguous & Low-Confidence Signal Handling (Class UNKNOWN, requires_review=True)
6. Requirement vs Classification Mismatch Detection (requires_review=True)
7. Entity Conflict Detection & Missing Optional Fields Resilience
8. Error Handling & Safe Failures (PDF_CORRUPTED, PASSWORD_PROTECTED_PDF, IMAGE_DECODE_FAILED, OCR_LOW_QUALITY)
9. Processing Lifecycle, Idempotency & Retry Recovery
10. Document Replacement & Soft-Removal Audit Trail Preservation
11. Multi-Tenant Security & Tenant Isolation (404 isolation across all telemetry endpoints)
12. Compliance Separation Guard (No PASS/FAIL, No Scoring, No AI Recommendation)
"""

import io
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
import numpy as np
import cv2
import pymupdf as fitz
from fastapi import UploadFile, HTTPException
from sqlalchemy import select
from starlette.datastructures import Headers

# Set Python path to backend root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
    ClassificationConfidenceLevel,
    DocumentClass,
    DocumentProcessing,
    ExtractionMethod,
    ProcessingStage,
    ProcessingStatus,
)
from app.services.document_classification_service import (
    classify_extracted_text,
    derive_expected_document_type,
)
from app.services.structured_extraction_service import (
    extract_structured_entities_from_text,
    normalize_date_string,
    parse_indian_currency_to_number,
)
from app.services.bid_document_service import (
    upload_bid_document,
    replace_bid_document,
    remove_bid_document,
)
from app.services.document_processing_service import (
    execute_document_processing_pipeline,
    queue_document_processing,
    retry_document_processing,
    get_document_processing,
    get_document_extracted_text,
    get_document_classification,
    get_document_extracted_data,
)


def create_synthetic_pdf(text: str) -> bytes:
    """Helper to generate an in-memory digital PDF with given text."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(50, 72), text, fontsize=11)
    buf = doc.tobytes()
    doc.close()
    return buf


def create_synthetic_text_image_bytes(text_lines: list[str]) -> bytes:
    """Generates an in-memory PNG image with clean rendered text using OpenCV."""
    canvas = np.full((600, 1000, 3), 255, dtype=np.uint8)
    y = 80
    for line in text_lines:
        cv2.putText(
            canvas,
            line,
            (50, y),
            cv2.FONT_HERSHEY_DUPLEX,
            0.80,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )
        y += 65

    success, buffer = cv2.imencode(".png", canvas)
    if not success:
        raise ValueError("Failed to encode synthetic test image.")
    return buffer.tobytes()


def create_scanned_pdf_with_image_bytes(text_lines: list[str]) -> bytes:
    """Creates a PDF containing an embedded bitmap image with no digital text fonts."""
    img_bytes = create_synthetic_text_image_bytes(text_lines)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    rect = fitz.Rect(40, 50, 555, 450)
    page.insert_image(rect, stream=img_bytes)
    buf = doc.tobytes()
    doc.close()
    return buf


def create_hybrid_pdf_bytes() -> bytes:
    """Creates a 2-page PDF: Page 1 Digital Text, Page 2 Scanned Image."""
    doc = fitz.open()
    
    # Page 1: Digital Text
    p1 = doc.new_page(width=595, height=842)
    p1_text = (
        "GOVERNMENT OF INDIA - MINISTRY OF COMMERCE AND INDUSTRY\n"
        "UDYAM REGISTRATION CERTIFICATE\n"
        "UDYAM REGISTRATION NUMBER: UDYAM-KR-03-0056789\n"
        "NAME OF ENTERPRISE: BHARAT DEFENCE SYSTEMS PRIVATE LIMITED\n"
        "MAJOR ACTIVITY: MANUFACTURING\n"
        "ENTERPRISE TYPE: MEDIUM\n"
        "DATE OF INCORPORATION: 15/08/2018\n"
    )
    p1.insert_text(fitz.Point(50, 72), p1_text, fontsize=11)

    # Page 2: Scanned Bitmap Image
    p2 = doc.new_page(width=595, height=842)
    p2_img_bytes = create_synthetic_text_image_bytes([
        "LOCAL CONTENT DECLARATION UNDER PPP-MII ORDER 2017",
        "We hereby declare that Local Content is 65.50 percent",
        "Location of Value Addition: Electronic City, Bengaluru",
    ])
    rect = fitz.Rect(40, 50, 555, 450)
    p2.insert_image(rect, stream=p2_img_bytes)

    buf = doc.tobytes()
    doc.close()
    return buf


def run_tests():
    print("=" * 80)
    print("BIDVERIFY AI — PART 4F MASTER INTEGRATION & CONFIDENCE QA TEST SUITE")
    print("=" * 80)

    db = get_session_factory()()

    try:
        # -------------------------------------------------------------------------
        # Setup: Self-contained Test Fixtures
        # -------------------------------------------------------------------------
        print("\n[Setup] Initializing test fixtures and tenant identities...")
        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()
        if not bidder_role:
            bidder_role = Role(name="BIDDER", description="Bidder Role")
            db.add(bidder_role)
            db.commit()
            db.refresh(bidder_role)

        proc_role = db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()
        if not proc_role:
            proc_role = Role(name="PROCUREMENT_OFFICER", description="Procurement Officer")
            db.add(proc_role)
            db.commit()
            db.refresh(proc_role)

        # Buyer Org & Officer
        buyer_org = Organization(
            name=f"Govt Procurement Dept 4F - {uuid.uuid4().hex[:6]}",
            organization_type="MINISTRY",
            is_active=True,
        )
        db.add(buyer_org)
        db.commit()
        db.refresh(buyer_org)

        officer_profile = Profile(
            organization_id=buyer_org.id,
            role_id=proc_role.id,
            full_name="Procurement Officer 4F",
            email=f"officer_4f_{uuid.uuid4().hex[:6]}@gem.gov.in",
            is_active=True,
        )
        db.add(officer_profile)
        db.commit()
        db.refresh(officer_profile)

        # Tender & Requirements
        tender = Tender(
            tender_number=f"GEM/2026/4F/{uuid.uuid4().hex[:6].upper()}",
            title="High Performance Computing Cluster & Network Infrastructure",
            description="GeM statutory procurement for national data center.",
            department="Ministry of Electronics and Information Technology",
            category="GOODS",
            estimated_value=12500000.00,
            submission_start_date=datetime.now(timezone.utc) - timedelta(days=1),
            submission_end_date=datetime.now(timezone.utc) + timedelta(days=15),
            status="OPEN",
            organization_id=buyer_org.id,
            created_by_profile_id=officer_profile.id,
            is_active=True,
        )
        db.add(tender)
        db.commit()
        db.refresh(tender)

        req_gst = TenderRequirement(
            tender_id=tender.id,
            code="REQ_GST",
            name="GST Registration Certificate",
            category="STATUTORY",
            requirement_type="DOCUMENT",
            is_mandatory=True,
        )
        req_pan = TenderRequirement(
            tender_id=tender.id,
            code="REQ_PAN",
            name="Permanent Account Number (PAN) Card",
            category="STATUTORY",
            requirement_type="DOCUMENT",
            is_mandatory=True,
        )
        req_udyam = TenderRequirement(
            tender_id=tender.id,
            code="REQ_UDYAM",
            name="Udyam MSME Certificate",
            category="TECHNICAL",
            requirement_type="DOCUMENT",
            is_mandatory=False,
        )
        db.add_all([req_gst, req_pan, req_udyam])
        db.commit()
        db.refresh(req_gst)
        db.refresh(req_pan)
        db.refresh(req_udyam)

        # Bidder 1 Setup
        org1 = Organization(
            name=f"Bharat Computing Solutions - {uuid.uuid4().hex[:6]}",
            organization_type="PRIVATE_LIMITED",
            registration_number=f"REG-4F-{uuid.uuid4().hex[:6]}",
            is_active=True,
        )
        db.add(org1)
        db.commit()
        db.refresh(org1)

        profile1 = Profile(
            organization_id=org1.id,
            role_id=bidder_role.id,
            full_name="Primary Bidder 4F",
            email=f"bidder1_4f_{uuid.uuid4().hex[:6]}@example.com",
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

        bid1 = Bid(
            tender_id=tender.id,
            bidder_organization_id=org1.id,
            created_by_profile_id=profile1.id,
            bid_number=f"BID-4F-{uuid.uuid4().hex[:6].upper()}",
            status="DRAFT",
            quoted_amount=11800000.00,
            currency="INR",
            technical_summary="Enterprise GPU compute node deployment.",
        )
        db.add(bid1)
        db.commit()
        db.refresh(user1)
        db.refresh(bid1)

        # Bidder 2 Setup (for cross-tenant checks)
        org2 = Organization(
            name=f"Competitor Systems Ltd - {uuid.uuid4().hex[:6]}",
            organization_type="PRIVATE_LIMITED",
            is_active=True,
        )
        db.add(org2)
        db.commit()
        db.refresh(org2)

        profile2 = Profile(
            organization_id=org2.id,
            role_id=bidder_role.id,
            full_name="Competitor Bidder 4F",
            email=f"bidder2_4f_{uuid.uuid4().hex[:6]}@example.com",
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

        print("  [PASS] Setup completed successfully.")

        # -------------------------------------------------------------------------
        # Test 1: Digital PDF Flow (PyMuPDF -> Classification -> Field Extraction)
        # -------------------------------------------------------------------------
        print("\n[Test 1] Testing Full End-to-End Digital PDF Flow (PyMuPDF -> Classification -> Extraction)...")
        gst_text = (
            "GOVERNMENT OF INDIA - GOODS AND SERVICES TAX\n"
            "FORM GST REG-06 - REGISTRATION CERTIFICATE\n"
            "Registration Number: 29AABCB1234F1Z5\n"
            "Legal Name: BHARAT COMPUTING SOLUTIONS PRIVATE LIMITED\n"
            "Trade Name: BHARAT COMPUTING\n"
            "Date of Liability: 01/07/2017\n"
            "Date of Validity: From 01/07/2017 To Permanent\n"
            "Type of Registration: Regular\n"
            "Principal Place of Business: Bangalore, Karnataka, 560001\n"
        )
        gst_pdf_bytes = create_synthetic_pdf(gst_text)

        doc_gst = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            tender_requirement_id=req_gst.id,
            document_type="GST_CERTIFICATE",
            file=UploadFile(
                filename="gst_registration_cert.pdf",
                file=io.BytesIO(gst_pdf_bytes),
                headers=Headers({"content-type": "application/pdf"}),
            ),
        )

        proc_gst = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_gst.id,
        )

        assert proc_gst.processing_status == ProcessingStatus.COMPLETED, f"Expected COMPLETED, got {proc_gst.processing_status}"
        assert proc_gst.processing_stage == ProcessingStage.COMPLETED
        assert proc_gst.extraction_method == ExtractionMethod.DIGITAL_PDF
        assert proc_gst.page_count == 1
        assert proc_gst.detected_document_type == DocumentClass.GST_CERTIFICATE
        assert proc_gst.classification_confidence >= 0.85
        assert proc_gst.classification_requires_review is False
        assert proc_gst.extracted_data is not None
        fields_gst = proc_gst.extracted_data.get("fields", {})
        assert fields_gst.get("gstin", {}).get("value") == "29AABCB1234F1Z5"
        assert "BHARAT COMPUTING" in fields_gst.get("legal_name", {}).get("value")
        assert fields_gst.get("gstin", {}).get("confidence", 0) >= 0.90
        print(f"  [PASS] Digital PDF processed: method={proc_gst.extraction_method}, class={proc_gst.detected_document_type}, gstin={fields_gst['gstin']['value']}")

        # -------------------------------------------------------------------------
        # Test 2: Scanned PDF Flow (OCR Fallback -> Classification -> Extraction)
        # -------------------------------------------------------------------------
        print("\n[Test 2] Testing Full End-to-End Scanned PDF Flow (OpenCV + PaddleOCR -> Classification -> Extraction)...")
        pan_scanned_bytes = create_scanned_pdf_with_image_bytes([
            "INCOME TAX DEPARTMENT - GOVT OF INDIA",
            "PERMANENT ACCOUNT NUMBER CARD",
            "PAN: ABCDE1234F",
            "NAME: RAJESH KUMAR SHARMA",
            "FATHER'S NAME: SURESH SHARMA",
            "DATE OF BIRTH: 12/04/1985",
        ])

        doc_pan = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            tender_requirement_id=req_pan.id,
            document_type="PAN",
            file=UploadFile(
                filename="scanned_pan_card.pdf",
                file=io.BytesIO(pan_scanned_bytes),
                headers=Headers({"content-type": "application/pdf"}),
            ),
        )

        proc_pan = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_pan.id,
        )

        assert proc_pan.extraction_method == ExtractionMethod.OCR
        assert proc_pan.detected_document_type == DocumentClass.PAN
        assert proc_pan.extracted_data is not None
        fields_pan = proc_pan.extracted_data.get("fields", {})
        assert fields_pan.get("pan_number", {}).get("value") == "ABCDE1234F"
        print(f"  [PASS] Scanned PDF processed: method={proc_pan.extraction_method}, class={proc_pan.detected_document_type}, pan={fields_pan['pan_number']['value']}")

        # -------------------------------------------------------------------------
        # Test 3: Standalone Image Flow (PNG -> OpenCV -> OCR -> Classification)
        # -------------------------------------------------------------------------
        print("\n[Test 3] Testing Full End-to-End Standalone Image Flow (PNG -> OpenCV -> PaddleOCR)...")
        img_bytes = create_synthetic_text_image_bytes([
            "GOVERNMENT OF INDIA - MINISTRY OF MSME",
            "UDYAM REGISTRATION CERTIFICATE",
            "UDYAM REGISTRATION NUMBER: UDYAM-KR-03-0012345",
            "NAME OF ENTERPRISE: BHARAT TECH SERVERS",
            "MAJOR ACTIVITY: SERVICES",
            "TYPE: SMALL",
        ])

        doc_img = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            tender_requirement_id=req_udyam.id,
            document_type="UDYAM_CERTIFICATE",
            file=UploadFile(
                filename="udyam_proof.png",
                file=io.BytesIO(img_bytes),
                headers=Headers({"content-type": "image/png"}),
            ),
        )

        proc_img = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_img.id,
        )

        assert proc_img.extraction_method == ExtractionMethod.OCR
        assert proc_img.detected_document_type == DocumentClass.UDYAM_CERTIFICATE
        fields_udyam = proc_img.extracted_data.get("fields", {})
        assert fields_udyam.get("udyam_registration_number", {}).get("value") == "UDYAM-KR-03-0012345"
        print(f"  [PASS] Image processed: method={proc_img.extraction_method}, class={proc_img.detected_document_type}, udyam={fields_udyam['udyam_registration_number']['value']}")

        # -------------------------------------------------------------------------
        # Test 4: Hybrid PDF Flow (Page 1 Digital + Page 2 Scanned)
        # -------------------------------------------------------------------------
        print("\n[Test 4] Testing Full End-to-End Hybrid PDF Flow (Page 1 Digital + Page 2 OCR)...")
        hybrid_bytes = create_hybrid_pdf_bytes()

        doc_hybrid = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            tender_requirement_id=None,
            document_type="TECHNICAL_DOCUMENT",
            file=UploadFile(
                filename="hybrid_submission_package.pdf",
                file=io.BytesIO(hybrid_bytes),
                headers=Headers({"content-type": "application/pdf"}),
            ),
        )

        proc_hybrid = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_hybrid.id,
        )

        assert proc_hybrid.extraction_method == ExtractionMethod.HYBRID
        assert proc_hybrid.page_count == 2
        assert proc_hybrid.raw_text is not None
        assert "UDYAM-KR-03-0056789" in proc_hybrid.raw_text
        assert "LOCAL CONTENT DECLARATION" in proc_hybrid.raw_text
        print(f"  [PASS] Hybrid PDF routed: method={proc_hybrid.extraction_method}, page_count={proc_hybrid.page_count}")

        # -------------------------------------------------------------------------
        # Test 5: Unknown / Ambiguous Document Handling
        # -------------------------------------------------------------------------
        print("\n[Test 5] Testing Low-Signal / Ambiguous Document Handling...")
        ambiguous_text = "This is a miscellaneous notice with general guidelines and terms of service."
        ambiguous_pdf = create_synthetic_pdf(ambiguous_text)

        doc_amb = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            tender_requirement_id=None,
            document_type="OTHER",
            file=UploadFile(
                filename="generic_notice.pdf",
                file=io.BytesIO(ambiguous_pdf),
                headers=Headers({"content-type": "application/pdf"}),
            ),
        )

        proc_amb = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_amb.id,
        )

        assert proc_amb.detected_document_type in [DocumentClass.OTHER, DocumentClass.UNKNOWN]
        assert proc_amb.classification_requires_review is True
        assert proc_amb.processing_status == ProcessingStatus.NEEDS_REVIEW
        print(f"  [PASS] Ambiguous document handled: class={proc_amb.detected_document_type}, status={proc_amb.processing_status}, requires_review={proc_amb.classification_requires_review}")

        # -------------------------------------------------------------------------
        # Test 6: Requirement vs Classification Mismatch Detection
        # -------------------------------------------------------------------------
        print("\n[Test 6] Testing Expected vs Detected Type Mismatch Review Gate...")
        # Uploading a PAN document against a GST Requirement
        pan_under_gst_req = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            tender_requirement_id=req_gst.id,
            document_type="PAN",
            file=UploadFile(
                filename="pan_uploaded_as_gst.pdf",
                file=io.BytesIO(create_synthetic_pdf("INCOME TAX DEPARTMENT - PERMANENT ACCOUNT NUMBER CARD: ABCDE9999Z - SMT ANITA ROY")),
                headers=Headers({"content-type": "application/pdf"}),
            ),
        )

        proc_mismatch = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=pan_under_gst_req.id,
        )

        class_res = get_document_classification(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=pan_under_gst_req.id,
        )

        assert proc_mismatch.detected_document_type == DocumentClass.PAN
        assert class_res.expected_document_type == DocumentClass.GST_CERTIFICATE
        assert proc_mismatch.classification_requires_review is True
        assert proc_mismatch.processing_status == ProcessingStatus.NEEDS_REVIEW
        assert "expected 'gst certificate'" in proc_mismatch.classification_reason.lower()
        print(f"  [PASS] Mismatch flagged: expected={class_res.expected_document_type}, detected={proc_mismatch.detected_document_type}, review_flag={proc_mismatch.classification_requires_review}")

        # -------------------------------------------------------------------------
        # Test 7: Entity Conflict Detection & Missing Optional Fields
        # -------------------------------------------------------------------------
        print("\n[Test 7] Testing Entity Conflict Detection and Missing Fields Resilience...")
        conflict_text = (
            "GOVERNMENT OF INDIA - GST REGISTRATION\n"
            "PRIMARY GSTIN: 29AAAAA0000A1Z5\n"
            "SECONDARY GSTIN FOR BRANCH: 29BBBBB1111B2Z6\n"
            "LEGAL NAME: CONFLICT CORP PRIVATE LIMITED\n"
        )
        doc_conflict = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            tender_requirement_id=None,
            document_type="GST_CERTIFICATE",
            file=UploadFile(
                filename="conflicting_gst.pdf",
                file=io.BytesIO(create_synthetic_pdf(conflict_text)),
                headers=Headers({"content-type": "application/pdf"}),
            ),
        )

        proc_conflict = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_conflict.id,
        )

        fields_conf = proc_conflict.extracted_data.get("fields", {})
        assert fields_conf.get("gstin", {}).get("is_conflict") is True
        assert proc_conflict.extraction_requires_review is True
        assert proc_conflict.processing_status == ProcessingStatus.NEEDS_REVIEW
        print("  [PASS] Multiple conflicting GSTIN identifiers flagged with is_conflict=True and review status.")

        # -------------------------------------------------------------------------
        # Test 8: Safe Resilience & Error Telemetry (Corrupted, Password-Protected, Decode Errors)
        # -------------------------------------------------------------------------
        print("\n[Test 8] Testing Resilience and Safe Failure Telemetry on Corrupt/Locked Files...")
        
        # 8a: Corrupted PDF
        doc_corrupt_pdf = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            tender_requirement_id=None,
            document_type="CORRUPT_PDF_DOC",
            file=UploadFile(
                filename="broken.pdf",
                file=io.BytesIO(b"%PDF-1.4\nBROKEN_GARBAGE_BYTES_NO_EOF"),
                headers=Headers({"content-type": "application/pdf"}),
            ),
        )
        proc_corrupt_pdf = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_corrupt_pdf.id,
        )
        assert proc_corrupt_pdf.processing_status == ProcessingStatus.FAILED
        assert proc_corrupt_pdf.error_code == "PDF_CORRUPTED"
        assert proc_corrupt_pdf.error_message is not None

        # 8b: Password-Protected PDF
        locked_doc = fitz.open()
        locked_doc.new_page().insert_text(fitz.Point(50, 72), "Confidential Protected Data")
        locked_bytes = locked_doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner123", user_pw="pass123")
        locked_doc.close()

        doc_locked = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            tender_requirement_id=None,
            document_type="PASSWORD_PROTECTED_DOC",
            file=UploadFile(
                filename="locked_contract.pdf",
                file=io.BytesIO(locked_bytes),
                headers=Headers({"content-type": "application/pdf"}),
            ),
        )
        proc_locked = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_locked.id,
        )
        assert proc_locked.processing_status == ProcessingStatus.FAILED
        assert proc_locked.error_code == "PASSWORD_PROTECTED_PDF"

        # 8c: Corrupted Image
        doc_corrupt_img = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            tender_requirement_id=None,
            document_type="CORRUPT_IMAGE_DOC",
            file=UploadFile(
                filename="bad_image.png",
                file=io.BytesIO(b"\x89PNG\r\n\x1a\nCORRUPT_PNG_CHUNKS"),
                headers=Headers({"content-type": "image/png"}),
            ),
        )
        proc_corrupt_img = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_corrupt_img.id,
        )
        assert proc_corrupt_img.processing_status == ProcessingStatus.FAILED
        assert proc_corrupt_img.error_code == "IMAGE_DECODE_FAILED"

        print("  [PASS] Corrupted PDF, locked PDF, and corrupted image gracefully handled with clean telemetry.")

        # -------------------------------------------------------------------------
        # Test 9: Idempotency & Retry Workflow
        # -------------------------------------------------------------------------
        print("\n[Test 9] Testing Processing Idempotency and Retry Workflow...")
        # 9a: Idempotency on completed doc
        repeat_proc = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_pan.id,
        )
        assert repeat_proc.id == proc_pan.id
        assert repeat_proc.processing_status == ProcessingStatus.COMPLETED

        # 9b: Retry on failed doc
        retried_proc = retry_document_processing(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_corrupt_pdf.id,
        )
        # Attempting retry on the same corrupt file will fail again deterministically with clean state reset
        assert retried_proc.id == proc_corrupt_pdf.id
        assert retried_proc.processing_status == ProcessingStatus.FAILED
        assert retried_proc.error_code == "PDF_CORRUPTED"

        print("  [PASS] Idempotency returned existing record and Retry performed clean state reset.")

        # -------------------------------------------------------------------------
        # Test 10: Document Replacement & Soft-Removal Audit Trail
        # -------------------------------------------------------------------------
        print("\n[Test 10] Testing Document Replacement and Removal History Preservation...")
        # Replace doc_pan with a new version
        new_pan_pdf = create_synthetic_pdf(
            "INCOME TAX DEPARTMENT - GOVT OF INDIA\n"
            "PERMANENT ACCOUNT NUMBER CARD\n"
            "PAN: ABCDE1234F\n"
            "NAME: RAJESH KUMAR SHARMA\n"
            "DATE OF BIRTH: 12/04/1985\n"
        )
        doc_v2 = replace_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_pan.id,
            file=UploadFile(
                filename="pan_registration_v2.pdf",
                file=io.BytesIO(new_pan_pdf),
                headers=Headers({"content-type": "application/pdf"}),
            ),
        )
        assert doc_v2.version == 2
        assert doc_v2.id != doc_pan.id

        # Verify doc_pan v1 processing record is preserved
        db.refresh(proc_pan)
        assert proc_pan.bid_document_id == doc_pan.id
        assert proc_pan.processing_status == ProcessingStatus.COMPLETED

        # Process doc_v2 independently
        proc_v2 = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_v2.id,
        )
        assert proc_v2.id != proc_pan.id
        assert proc_v2.bid_document_id == doc_v2.id
        assert proc_v2.processing_status == ProcessingStatus.COMPLETED

        print("  [PASS] Document replacement preserved v1 audit record and processed v2 independently.")

        # -------------------------------------------------------------------------
        # Test 11: Multi-Tenant Security & Tenant Isolation
        # -------------------------------------------------------------------------
        print("\n[Test 11] Testing Strict Multi-Tenant Security and Isolation (Bidder 2 accessing Bidder 1)...")
        # Bidder 2 attempts to query Bidder 1's processing telemetry
        try:
            get_document_processing(db=db, current_user=user2, bid_id=bid1.id, document_id=doc_v2.id)
            assert False, "Bidder 2 should not access Bidder 1 document processing"
        except HTTPException as e:
            assert e.status_code == 404

        # Bidder 2 attempts to query Bidder 1's extracted text
        try:
            get_document_extracted_text(db=db, current_user=user2, bid_id=bid1.id, document_id=doc_v2.id)
            assert False, "Bidder 2 should not access Bidder 1 extracted text"
        except HTTPException as e:
            assert e.status_code == 404

        # Bidder 2 attempts to query Bidder 1's classification
        try:
            get_document_classification(db=db, current_user=user2, bid_id=bid1.id, document_id=doc_v2.id)
            assert False, "Bidder 2 should not access Bidder 1 classification"
        except HTTPException as e:
            assert e.status_code == 404

        # Bidder 2 attempts to query Bidder 1's structured extracted data
        try:
            get_document_extracted_data(db=db, current_user=user2, bid_id=bid1.id, document_id=doc_v2.id)
            assert False, "Bidder 2 should not access Bidder 1 structured data"
        except HTTPException as e:
            assert e.status_code == 404

        print("  [PASS] Cross-tenant access to processing, text, classification, and structured data safely rejected with HTTP 404.")

        # -------------------------------------------------------------------------
        # Test 12: Compliance Separation Guard
        # -------------------------------------------------------------------------
        print("\n[Test 12] Testing Strict Separation of Document Processing from Compliance Engine...")
        # Confirm that DocumentProcessing records and responses contain NO compliance PASS/FAIL, scores, or AI recommendations
        assert not hasattr(proc_v2, "compliance_status"), "DocumentProcessing should not have compliance_status"
        assert not hasattr(proc_v2, "compliance_score"), "DocumentProcessing should not have compliance_score"
        assert not hasattr(proc_v2, "risk_level"), "DocumentProcessing should not have risk_level"
        assert not hasattr(proc_v2, "ai_recommendation"), "DocumentProcessing should not have ai_recommendation"
        
        # Verify extracted_data only contains structured entities with field-level evidence
        fields = proc_v2.extracted_data.get("fields", {})
        for fname, fval in fields.items():
            assert "value" in fval
            assert "confidence" in fval
            assert "evidence" in fval
            assert "pass" not in fval
            assert "compliant" not in fval

        print("  [PASS] Verified 100% compliance boundary integrity. Document processing output is strictly un-evaluated and ready for Part 5.")

        print("\n" + "=" * 80)
        print("ALL 12/12 PART 4F MASTER INTEGRATION & QA TESTS PASSED (100% SUCCESS)")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    run_tests()
