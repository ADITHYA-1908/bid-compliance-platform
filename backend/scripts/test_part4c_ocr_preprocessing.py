"""
Part 4C Master Integration & Regression Test Suite
Tests OCR & Image Preprocessing:
- Unit test: OpenCV Image Preprocessing (grayscale, bilateral filtering, CLAHE, sharpness)
- Unit test: PyMuPDF Page-to-Image 200 DPI rendering
- Integration test: Standalone image (PNG/JPG) OCR extraction & token preservation
- Integration test: Scanned/image-only PDF OCR extraction
- Integration test: Hybrid PDF processing (Page 1 digital, Page 2 scanned)
- Integration test: Low-quality / blank scan handling (NEEDS_REVIEW / OCR_LOW_QUALITY)
- Integration test: Corrupted image failure handling (IMAGE_DECODE_FAILED)
- Integration test: Idempotency of repeated OCR calls
- Integration test: Retry workflow on failed/low-quality documents
- Integration test: Cross-tenant security & SUBMITTED bid document access
"""

import os
import sys
import io
import uuid
from datetime import datetime, timezone, timedelta
import numpy as np
import cv2
import fitz  # PyMuPDF
from fastapi import UploadFile, HTTPException
from sqlalchemy import select
from starlette.datastructures import Headers

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
    execute_document_processing_pipeline,
    queue_document_processing,
    retry_document_processing,
    get_document_extracted_text,
)
from app.services.image_preprocessing_service import (
    preprocess_document_image,
    calculate_image_sharpness,
    load_image_bytes_to_cv2,
    render_pdf_page_to_image,
    ImagePreprocessingError,
)
from app.services.ocr_service import (
    process_document_with_ocr,
    OCRExtractionError,
)


def create_synthetic_text_image_bytes(text_lines: list[str]) -> bytes:
    """Generates an in-memory PNG image with clean rendered text using OpenCV."""
    # Create white canvas (height=600, width=1000, 3 channels)
    canvas = np.full((600, 1000, 3), 255, dtype=np.uint8)
    
    y = 80
    for line in text_lines:
        cv2.putText(
            canvas,
            line,
            (50, y),
            cv2.FONT_HERSHEY_DUPLEX,
            0.85,
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
    """Creates a PDF containing an embedded bitmap image with no digital font glyphs (pure scanned PDF)."""
    img_bytes = create_synthetic_text_image_bytes(text_lines)
    
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 standard points
    
    # Insert image as full page background/pixmap (scanned page)
    rect = fitz.Rect(40, 50, 555, 450)
    page.insert_image(rect, stream=img_bytes)
    
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_hybrid_pdf_bytes() -> bytes:
    """Creates a 2-page hybrid PDF: Page 1 has digital selectable text, Page 2 is a scanned image."""
    doc = fitz.open()
    
    # Page 1: Digital Selectable Text
    page1 = doc.new_page(width=595, height=842)
    p1_text = (
        "GOVERNMENT E-MARKETPLACE STATUTORY BID DECLARATION\n"
        "Tender ID: GEM/2026/B/HYBRID-8877\n"
        "Organization: Apex Cybernetics Enterprise Pvt Ltd\n"
        "PAN Number: ABCDE1234F\n"
        "GSTIN Number: 33ABCDE1234F1Z5\n"
        "Total Quoted Bid Price: INR 5,00,00,000 (Five Crore INR)\n"
    )
    page1.insert_text((50, 72), p1_text, fontsize=11)
    
    # Page 2: Scanned Image Page
    page2 = doc.new_page(width=595, height=842)
    p2_img_bytes = create_synthetic_text_image_bytes([
        "SCHEDULE B: OEM AUTHORIZATION & MSME REGISTRATION",
        "Udyam MSME Registration: UDYAM-TN-00-1234567",
        "Make In India Local Content: 50% Verified",
        "Authorized Signatory Date: 2026-08-26",
    ])
    rect = fitz.Rect(40, 50, 555, 450)
    page2.insert_image(rect, stream=p2_img_bytes)
    
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def run_tests():
    print("=" * 80)
    print("BIDVERIFY AI — PART 4C OCR & IMAGE PREPROCESSING TEST SUITE")
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
            name=f"Test Part4C Org 1 - {uuid.uuid4().hex[:6]}",
            organization_type="PRIVATE_LIMITED",
            registration_number=f"REG-4C-{uuid.uuid4().hex[:6]}",
            is_active=True,
        )
        db.add(org1)
        db.commit()
        db.refresh(org1)

        profile1 = Profile(
            organization_id=org1.id,
            role_id=bidder_role.id,
            full_name="Bidder One P4C",
            email=f"bidder1_p4c_{uuid.uuid4().hex[:6]}@example.com",
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
            name=f"Test Part4C Org 2 - {uuid.uuid4().hex[:6]}",
            organization_type="PRIVATE_LIMITED",
            is_active=True,
        )
        db.add(org2)
        db.commit()
        db.refresh(org2)

        profile2 = Profile(
            organization_id=org2.id,
            role_id=bidder_role.id,
            full_name="Bidder Two P4C",
            email=f"bidder2_p4c_{uuid.uuid4().hex[:6]}@example.com",
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
            tender_number=f"GEM/2026/B/P4C-{uuid.uuid4().hex[:6]}",
            title="Part 4C OCR Preprocessing Tender",
            description="Testing OCR & Image Preprocessing pipeline",
            status="OPEN",
            submission_start_date=datetime.now(timezone.utc) - timedelta(days=1),
            submission_end_date=datetime.now(timezone.utc) + timedelta(days=30),
            estimated_value=6000000.0,
            currency="INR",
            organization_id=org1.id,
            created_by_profile_id=profile1.id,
        )
        db.add(tender)
        db.commit()
        db.refresh(tender)

        req1 = TenderRequirement(
            tender_id=tender.id,
            code="REQ-OCR-01",
            name="Scanned Certificate Evidence",
            requirement_type="DOCUMENT",
            is_mandatory=True,
            is_active=True,
        )
        db.add(req1)
        db.commit()

        bid1 = Bid(
            tender_id=tender.id,
            bidder_organization_id=org1.id,
            created_by_profile_id=profile1.id,
            bid_number=f"BID-P4C-{uuid.uuid4().hex[:6]}",
            status="DRAFT",
            quoted_amount=5800000.0,
            currency="INR",
        )
        db.add(bid1)
        db.commit()
        db.refresh(bid1)
        print("  [PASS] Setup completed successfully.")

        # ---------------------------------------------------------------------
        # TEST 1: Unit Test — OpenCV Image Preprocessing Pipeline
        # ---------------------------------------------------------------------
        print("\n[Test 1] Testing OpenCV image preprocessing pipeline...")
        img_raw_bytes = create_synthetic_text_image_bytes([
            "PAN: ABCDE1234F",
            "GSTIN: 33ABCDE1234F1Z5",
            "UDYAM: UDYAM-TN-00-1234567",
        ])
        cv2_mat = load_image_bytes_to_cv2(img_raw_bytes)
        assert cv2_mat is not None
        assert len(cv2_mat.shape) == 3

        sharpness = calculate_image_sharpness(cv2_mat)
        assert sharpness > 0.0

        preprocessed = preprocess_document_image(cv2_mat, enhance_contrast=True, denoise=True)
        assert preprocessed is not None
        assert len(preprocessed.shape) == 2  # Grayscale
        print(f"  [PASS] OpenCV preprocessing succeeded (dimensions={preprocessed.shape}, sharpness={sharpness:.1f}).")

        # ---------------------------------------------------------------------
        # TEST 2: Unit Test — PyMuPDF Page-to-Image Rendering at 200 DPI
        # ---------------------------------------------------------------------
        print("\n[Test 2] Testing PyMuPDF 200 DPI page rendering...")
        scanned_pdf_bytes = create_scanned_pdf_with_image_bytes([
            "GOVERNMENT PROCUREMENT STATUTORY PROOF",
            "PAN: ABCDE1234F",
            "UDYAM: UDYAM-TN-00-1234567",
        ])
        page_img = render_pdf_page_to_image(scanned_pdf_bytes, page_number=1, dpi=200)
        assert page_img is not None
        assert len(page_img.shape) == 3
        assert page_img.shape[0] > 1000  # A4 height rendered at 200 DPI
        print(f"  [PASS] PyMuPDF rendered page 1 to image matrix {page_img.shape} at 200 DPI.")

        # ---------------------------------------------------------------------
        # TEST 3: Integration Test — Standalone Image OCR Extraction (PNG)
        # ---------------------------------------------------------------------
        print("\n[Test 3] Testing standalone image (PNG) OCR text extraction...")
        upload_img_res = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            file=UploadFile(
                file=io.BytesIO(img_raw_bytes),
                size=len(img_raw_bytes),
                filename="scanned_pan_card.png",
                headers=Headers({"content-type": "image/png"}),
            ),
            document_type="STATUTORY_DOCUMENT",
            tender_requirement_id=req1.id,
        )

        proc_img = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_img_res.id,
        )

        assert proc_img.extraction_method == ExtractionMethod.OCR
        assert proc_img.page_count == 1
        assert proc_img.processing_stage in [
            ProcessingStage.CLASSIFICATION,
            ProcessingStage.STRUCTURED_EXTRACTION,
            ProcessingStage.COMPLETED,
        ]
        assert proc_img.raw_text is not None
        assert proc_img.normalized_text is not None
        assert len(proc_img.normalized_text) > 10
        assert "ABCDE1234F" in proc_img.normalized_text or "PAN" in proc_img.normalized_text
        print(f"  [PASS] Standalone image OCR succeeded (method={proc_img.extraction_method}, text_len={len(proc_img.normalized_text)}).")

        # ---------------------------------------------------------------------
        # TEST 4: Integration Test — Scanned PDF OCR Extraction
        # ---------------------------------------------------------------------
        print("\n[Test 4] Testing scanned PDF OCR text extraction...")
        upload_scan_pdf_res = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            file=UploadFile(
                file=io.BytesIO(scanned_pdf_bytes),
                size=len(scanned_pdf_bytes),
                filename="scanned_statutory_cert.pdf",
                headers=Headers({"content-type": "application/pdf"}),
            ),
            document_type="STATUTORY_DOCUMENT",
        )

        proc_scan_pdf = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_scan_pdf_res.id,
        )

        assert proc_scan_pdf.extraction_method == ExtractionMethod.OCR
        assert proc_scan_pdf.page_count == 1
        assert proc_scan_pdf.processing_stage in [
            ProcessingStage.CLASSIFICATION,
            ProcessingStage.STRUCTURED_EXTRACTION,
            ProcessingStage.COMPLETED,
        ]
        assert proc_scan_pdf.raw_text is not None
        assert len(proc_scan_pdf.normalized_text) > 10
        assert "ABCDE1234F" in proc_scan_pdf.normalized_text or "PAN" in proc_scan_pdf.normalized_text or "UDYAM" in proc_scan_pdf.normalized_text
        print(f"  [PASS] Scanned PDF OCR succeeded (method={proc_scan_pdf.extraction_method}, stage={proc_scan_pdf.processing_stage}).")

        # ---------------------------------------------------------------------
        # TEST 5: Integration Test — Hybrid PDF Processing
        # ---------------------------------------------------------------------
        print("\n[Test 5] Testing hybrid PDF processing (Page 1 digital, Page 2 scanned)...")
        hybrid_pdf_bytes = create_hybrid_pdf_bytes()
        upload_hybrid_res = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            file=UploadFile(
                file=io.BytesIO(hybrid_pdf_bytes),
                size=len(hybrid_pdf_bytes),
                filename="hybrid_bid_proposal.pdf",
                headers=Headers({"content-type": "application/pdf"}),
            ),
            document_type="TECHNICAL_DOCUMENT",
        )

        proc_hybrid = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_hybrid_res.id,
        )

        assert proc_hybrid.extraction_method == ExtractionMethod.HYBRID
        assert proc_hybrid.page_count == 2
        assert proc_hybrid.processing_stage in [
            ProcessingStage.CLASSIFICATION,
            ProcessingStage.STRUCTURED_EXTRACTION,
            ProcessingStage.COMPLETED,
        ]
        assert "--- Page 1 ---" in proc_hybrid.raw_text
        assert "--- Page 2 ---" in proc_hybrid.raw_text
        assert "ABCDE1234F" in proc_hybrid.normalized_text
        assert "UDYAM-TN-00-1234567" in proc_hybrid.normalized_text
        print(f"  [PASS] Hybrid PDF correctly routed (Page 1 Digital + Page 2 OCR -> method={proc_hybrid.extraction_method}).")

        # ---------------------------------------------------------------------
        # TEST 6: Integration Test — Low-Quality / Blank Scan Handling
        # ---------------------------------------------------------------------
        print("\n[Test 6] Testing low-quality / blank scan handling...")
        # Create empty white image (0 text characters)
        blank_canvas = np.full((300, 300, 3), 255, dtype=np.uint8)
        _, blank_buf = cv2.imencode(".png", blank_canvas)
        blank_bytes = blank_buf.tobytes()

        upload_blank_res = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            file=UploadFile(
                file=io.BytesIO(blank_bytes),
                size=len(blank_bytes),
                filename="blank_scan_page.png",
                headers=Headers({"content-type": "image/png"}),
            ),
            document_type="TECHNICAL_DOCUMENT",
        )

        proc_blank = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_blank_res.id,
        )

        assert proc_blank.processing_status in [ProcessingStatus.NEEDS_REVIEW, ProcessingStatus.FAILED]
        assert proc_blank.error_code == "OCR_LOW_QUALITY"
        print("  [PASS] Blank/low-quality scan safely marked as NEEDS_REVIEW without fabricating text.")

        # ---------------------------------------------------------------------
        # TEST 7: Integration Test — Corrupted Image Binary Handling
        # ---------------------------------------------------------------------
        print("\n[Test 7] Testing corrupted image binary failure handling...")
        corrupt_img_bytes = b"NOT_A_VALID_IMAGE_BINARY_CORRUPTED_STREAM"
        upload_corrupt_img = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            file=UploadFile(
                file=io.BytesIO(corrupt_img_bytes),
                size=len(corrupt_img_bytes),
                filename="corrupted_scan.png",
                headers=Headers({"content-type": "image/png"}),
            ),
            document_type="FINANCIAL_DOCUMENT",
        )

        proc_corrupt = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_corrupt_img.id,
        )

        assert proc_corrupt.processing_status == ProcessingStatus.FAILED
        assert proc_corrupt.error_code in ["IMAGE_DECODE_FAILED", "PROCESSING_UNEXPECTED_ERROR"]
        print(f"  [PASS] Corrupted image recorded clean error telemetry [{proc_corrupt.error_code}].")

        # ---------------------------------------------------------------------
        # TEST 8: Integration Test — Idempotency of Repeated OCR Calls
        # ---------------------------------------------------------------------
        print("\n[Test 8] Testing idempotency of repeated OCR calls...")
        repeat_ocr_proc = queue_document_processing(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_img_res.id,
        )
        assert repeat_ocr_proc.extraction_method == ExtractionMethod.OCR
        assert repeat_ocr_proc.page_count == 1
        print("  [PASS] Repeated processing returned existing OCR results safely.")

        # ---------------------------------------------------------------------
        # TEST 9: Integration Test — Retry Flow on Low-Quality / Failed Documents
        # ---------------------------------------------------------------------
        print("\n[Test 9] Testing retry flow on NEEDS_REVIEW document...")
        retried_blank = retry_document_processing(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_blank_res.id,
        )
        assert retried_blank.processing_status in [ProcessingStatus.NEEDS_REVIEW, ProcessingStatus.FAILED]
        print("  [PASS] Retry successfully reset and re-executed processing pipeline.")

        # ---------------------------------------------------------------------
        # TEST 10: Integration Test — Cross-Tenant Security & Access on SUBMITTED Bids
        # ---------------------------------------------------------------------
        print("\n[Test 10] Testing cross-tenant isolation & SUBMITTED bid document access...")
        # Bidder 1 retrieves OCR extracted text
        text_resp = get_document_extracted_text(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_img_res.id,
        )
        assert text_resp.extraction_method == ExtractionMethod.OCR
        assert "ABCDE1234F" in text_resp.normalized_text

        # Bidder 2 attempts to read Bidder 1's OCR extracted text -> 404
        try:
            get_document_extracted_text(
                db=db,
                current_user=user2,
                bid_id=bid1.id,
                document_id=upload_img_res.id,
            )
            assert False, "Bidder 2 should not be able to read Bidder 1 OCR text"
        except HTTPException as he:
            assert he.status_code == 404
            print("  [PASS] Cross-tenant OCR text access safely rejected with HTTP 404.")

        # Mark bid as SUBMITTED and verify OCR text retrieval is allowed
        bid1.status = "SUBMITTED"
        bid1.submitted_at = datetime.now(timezone.utc)
        db.commit()

        submitted_ocr_text = get_document_extracted_text(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_hybrid_res.id,
        )
        assert submitted_ocr_text.extraction_method == ExtractionMethod.HYBRID
        print("  [PASS] OCR extracted text successfully retrieved on SUBMITTED bids.")

        print("\n" + "=" * 80)
        print("ALL 10/10 PART 4C INTEGRATION TESTS PASSED (100% SUCCESS)")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    run_tests()
