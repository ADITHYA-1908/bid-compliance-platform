"""
Test Suite for Part 4D: Document Classification
Tests deterministic rule-based document classification across GST, PAN, Udyam, OEM,
Financials, Turnover, Experience, Local Content, Blacklist declarations, Ambiguous text,
and Mismatches against Tender Requirements.
"""

import io
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
import pymupdf as fitz
import numpy as np
import cv2
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
from app.services.bid_document_service import upload_bid_document, replace_bid_document
from app.services.document_processing_service import (
    execute_document_processing_pipeline,
    get_document_classification,
)


def create_synthetic_pdf(text: str) -> bytes:
    """Helper to generate an in-memory PDF with given text."""
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


def run_tests():
    print("=" * 80)
    print("BIDVERIFY AI — PART 4D DOCUMENT CLASSIFICATION TEST SUITE")
    print("=" * 80)

    db = get_session_factory()()

    try:
        # -------------------------------------------------------------------------
        # Setup: Self-contained Test Fixtures
        # -------------------------------------------------------------------------
        print("\n[Setup] Initializing test fixtures...")
        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()
        if not bidder_role:
            bidder_role = Role(name="BIDDER", description="Bidder Role")
            db.add(bidder_role)
            db.commit()
            db.refresh(bidder_role)

        # Bidder 1 Setup
        org1 = Organization(
            name=f"Test Part4D Org 1 - {uuid.uuid4().hex[:6]}",
            organization_type="PRIVATE_LIMITED",
            registration_number=f"REG-4D-{uuid.uuid4().hex[:6]}",
            is_active=True,
        )
        db.add(org1)
        db.commit()
        db.refresh(org1)

        profile1 = Profile(
            organization_id=org1.id,
            role_id=bidder_role.id,
            full_name="Bidder One P4D",
            email=f"bidder1_p4d_{uuid.uuid4().hex[:6]}@example.com",
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
            name=f"Test Part4D Org 2 - {uuid.uuid4().hex[:6]}",
            organization_type="PRIVATE_LIMITED",
            is_active=True,
        )
        db.add(org2)
        db.commit()
        db.refresh(org2)

        profile2 = Profile(
            organization_id=org2.id,
            role_id=bidder_role.id,
            full_name="Bidder Two P4D",
            email=f"bidder2_p4d_{uuid.uuid4().hex[:6]}@example.com",
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
            tender_number=f"GEM/2026/B/P4D-{uuid.uuid4().hex[:6]}",
            title="Part 4D Document Classification Tender",
            description="Testing deterministic document classification pipeline",
            status="OPEN",
            submission_start_date=datetime.now(timezone.utc) - timedelta(days=1),
            submission_end_date=datetime.now(timezone.utc) + timedelta(days=30),
            estimated_value=7500000.0,
            currency="INR",
            organization_id=org1.id,
            created_by_profile_id=profile1.id,
        )
        db.add(tender)
        db.commit()
        db.refresh(tender)

        req_gst = TenderRequirement(
            tender_id=tender.id,
            code="REQ-GST-01",
            name="GST Registration Certificate",
            category="STATUTORY",
            requirement_type="DOCUMENT",
            is_mandatory=True,
            is_active=True,
        )
        db.add(req_gst)

        req_oem = TenderRequirement(
            tender_id=tender.id,
            code="REQ-OEM-01",
            name="OEM Authorization Letter (MAF)",
            category="TECHNICAL",
            requirement_type="DOCUMENT",
            is_mandatory=True,
            is_active=True,
        )
        db.add(req_oem)
        db.commit()

        bid1 = Bid(
            tender_id=tender.id,
            bidder_organization_id=org1.id,
            created_by_profile_id=profile1.id,
            bid_number=f"BID-P4D-{uuid.uuid4().hex[:6]}",
            status="DRAFT",
            quoted_amount=7200000.0,
            currency="INR",
        )
        db.add(bid1)
        db.commit()
        db.refresh(bid1)

        print("  [PASS] Setup completed successfully.")

        # -------------------------------------------------------------------------
        # Test 1: Deterministic Classifier — Statutory Document Classes
        # -------------------------------------------------------------------------
        print("\n[Test 1] Testing deterministic classification across statutory documents...")
        gst_sample = (
            "Government of India\n"
            "Form GST REG-06\n"
            "Registration Certificate\n"
            "Goods and Services Tax\n"
            "Registration Number: 33ABCDE1234F1Z5\n"
            "Legal Name: Acme Tech Solutions Private Limited\n"
            "Trade Name: Acme Technologies\n"
            "Constitution of Business: Private Limited Company\n"
        )
        res_gst = classify_extracted_text(gst_sample, original_filename="gst_certificate.pdf")
        assert res_gst.detected_document_type == DocumentClass.GST_CERTIFICATE, f"Expected GST_CERTIFICATE, got {res_gst.detected_document_type}"
        assert res_gst.confidence >= 0.80, f"Expected high confidence, got {res_gst.confidence}"
        assert res_gst.confidence_level == ClassificationConfidenceLevel.HIGH
        assert "GST" in res_gst.reason

        pan_sample = (
            "INCOME TAX DEPARTMENT\n"
            "GOVT. OF INDIA\n"
            "Permanent Account Number Card\n"
            "PAN: ABCDE1234F\n"
            "Name: RAJESH KUMAR SHARMA\n"
            "Father's Name: SURESH KUMAR SHARMA\n"
            "Date of Birth: 15/08/1985\n"
        )
        res_pan = classify_extracted_text(pan_sample, original_filename="pan_card.pdf")
        assert res_pan.detected_document_type == DocumentClass.PAN, f"Expected PAN, got {res_pan.detected_document_type}"
        assert res_pan.confidence >= 0.80

        udyam_sample = (
            "Ministry of Micro, Small and Medium Enterprises\n"
            "UDYAM REGISTRATION CERTIFICATE\n"
            "UDYAM REGISTRATION NUMBER: UDYAM-TN-00-1234567\n"
            "NAME OF ENTERPRISE: TECH FLOW SYSTEMS\n"
            "MAJOR ACTIVITY: MANUFACTURING\n"
            "ENTERPRISE TYPE: MICRO\n"
        )
        res_udyam = classify_extracted_text(udyam_sample, original_filename="udyam_registration.pdf")
        assert res_udyam.detected_document_type == DocumentClass.UDYAM_CERTIFICATE
        assert res_udyam.confidence >= 0.80
        print("  [PASS] GST, PAN, and Udyam statutory classes correctly identified with HIGH confidence.")

        # -------------------------------------------------------------------------
        # Test 2: Commercial & Technical Document Classes
        # -------------------------------------------------------------------------
        print("\n[Test 2] Testing OEM, Financial, Turnover, Experience, and MII Classes...")
        oem_sample = (
            "MANUFACTURERS AUTHORIZATION FORM (MAF)\n"
            "OEM AUTHORIZATION LETTER\n"
            "Ref: OEM/AUTH/2026/08\n"
            "We, Cisco Systems Inc, Original Equipment Manufacturer of networking equipment,\n"
            "hereby authorize M/s Acme Solutions as our Authorized Partner and Reseller\n"
            "to submit a bid response for GeM Tender GEM/2026/B/88991.\n"
            "We confirm full warranty support and technical assistance.\n"
        )
        res_oem = classify_extracted_text(oem_sample, original_filename="maf_cisco.pdf")
        assert res_oem.detected_document_type == DocumentClass.OEM_AUTHORIZATION
        assert res_oem.confidence >= 0.80

        fin_sample = (
            "Independent Auditor's Report\n"
            "Audited Financial Statements\n"
            "Balance Sheet as at 31st March 2025\n"
            "Statement of Profit and Loss\n"
            "Cash Flow Statement\n"
            "Total Revenue from operations: Rs. 15,40,00,000\n"
            "Equity and Liabilities: Current Assets and Non-Current Assets\n"
            "Notes forming part of the financial statements.\n"
        )
        res_fin = classify_extracted_text(fin_sample, original_filename="audited_balance_sheet.pdf")
        assert res_fin.detected_document_type == DocumentClass.FINANCIAL_STATEMENT

        turnover_sample = (
            "CA CERTIFICATE OF ANNUAL TURNOVER\n"
            "This is to certify that M/s Zenith Enterprises has achieved the following Annual Gross Turnover:\n"
            "FY 2022-23: Rs. 4,50,00,000\n"
            "FY 2023-24: Rs. 5,20,00,000\n"
            "FY 2024-25: Rs. 6,10,00,000\n"
            "Average Annual Turnover: Rs. 5.26 Crores\n"
            "Chartered Accountant Membership No: 123456\n"
            "UDIN: 24123456AAAAAB1234\n"
        )
        res_to = classify_extracted_text(turnover_sample, original_filename="turnover_certificate.pdf")
        assert res_to.detected_document_type == DocumentClass.TURNOVER_CERTIFICATE

        exp_sample = (
            "WORK COMPLETION CERTIFICATE\n"
            "Experience Certificate\n"
            "This is to certify that M/s Apex Infra has successfully completed the supply,\n"
            "installation and commissioning under Purchase Order PO/2023/4412\n"
            "Satisfactory performance and satisfactory completion recorded.\n"
            "Total contract value: Rs. 85,00,000.\n"
        )
        res_exp = classify_extracted_text(exp_sample, original_filename="completion_cert.pdf")
        assert res_exp.detected_document_type == DocumentClass.EXPERIENCE_CERTIFICATE

        mii_sample = (
            "LOCAL CONTENT DECLARATION\n"
            "Preference to Make in India Policy\n"
            "We hereby declare that our offered product meets the requirement of Class-I Local Supplier\n"
            "Percentage of Local Content is 65% with local value addition carried out at Chennai, Tamil Nadu.\n"
        )
        res_mii = classify_extracted_text(mii_sample, original_filename="make_in_india.pdf")
        assert res_mii.detected_document_type == DocumentClass.LOCAL_CONTENT_DECLARATION

        blacklist_sample = (
            "NON-BLACKLISTING DECLARATION\n"
            "Self Declaration Undertaking\n"
            "We hereby solemnly declare and affirm that our firm has not been blacklisted or debarred\n"
            "by any Central / State Government department, PSU, or GeM procurement portal.\n"
        )
        res_bl = classify_extracted_text(blacklist_sample, original_filename="non_blacklisting.pdf")
        assert res_bl.detected_document_type == DocumentClass.BLACKLIST_DECLARATION
        print("  [PASS] All 6 commercial/technical/undertaking document classes cleanly classified.")

        # -------------------------------------------------------------------------
        # Test 3: Anti-Collision — GST vs. PAN
        # -------------------------------------------------------------------------
        print("\n[Test 3] Testing anti-collision (GST certificate containing PAN string)...")
        gst_with_pan_mention = (
            "Form GST REG-06\n"
            "Government of India\n"
            "Goods and Services Tax Registration Certificate\n"
            "GSTIN: 33ABCDE1234F1Z5\n"
            "PAN of the Entity: ABCDE1234F\n"
            "Legal Name: Prime Software Pvt Ltd\n"
        )
        res_collision = classify_extracted_text(gst_with_pan_mention, original_filename="gst_reg.pdf")
        assert res_collision.detected_document_type == DocumentClass.GST_CERTIFICATE, f"Expected GST_CERTIFICATE, got {res_collision.detected_document_type}"
        print("  [PASS] GST certificate with embedded PAN correctly classified as GST_CERTIFICATE.")

        # -------------------------------------------------------------------------
        # Test 4: Ambiguous / Unknown Document Handling
        # -------------------------------------------------------------------------
        print("\n[Test 4] Testing unknown / ambiguous text handling...")
        ambiguous_text = "This is a random document with general terms regarding products, deliveries, and standard packaging rules without statutory markers."
        res_ambiguous = classify_extracted_text(ambiguous_text, original_filename="general_note.pdf")
        assert res_ambiguous.detected_document_type == DocumentClass.UNKNOWN
        assert res_ambiguous.requires_review is True
        assert res_ambiguous.confidence_level == ClassificationConfidenceLevel.LOW

        empty_text = "   "
        res_empty = classify_extracted_text(empty_text, original_filename="blank.pdf")
        assert res_empty.detected_document_type == DocumentClass.UNKNOWN
        assert res_empty.confidence == 0.0
        assert res_empty.requires_review is True
        print("  [PASS] Ambiguous and empty texts safely classified as UNKNOWN with review required.")

        # -------------------------------------------------------------------------
        # Test 5: Expected vs Detected Mismatch Detection
        # -------------------------------------------------------------------------
        print("\n[Test 5] Testing expected vs detected mismatch detection...")
        # Uploading PAN text for a requirement expecting GST
        res_mismatch = classify_extracted_text(
            pan_sample,
            original_filename="pan.pdf",
            requirement=req_gst,
        )
        assert res_mismatch.detected_document_type == DocumentClass.PAN
        assert res_mismatch.expected_document_type == DocumentClass.GST_CERTIFICATE
        assert res_mismatch.requires_review is True
        assert "requirement expected 'gst certificate'" in res_mismatch.reason.lower()
        print("  [PASS] Document mismatch cleanly flagged with requires_review=True and clear explainability.")

        # -------------------------------------------------------------------------
        # Test 6: Digital PDF Ingestion -> Text Extraction -> Classification Flow
        # -------------------------------------------------------------------------
        print("\n[Test 6] Testing Digital PDF full pipeline (Ingestion -> PyMuPDF -> Classification)...")
        gst_pdf_bytes = create_synthetic_pdf(gst_sample)
        upload_file = UploadFile(
            file=io.BytesIO(gst_pdf_bytes),
            size=len(gst_pdf_bytes),
            filename="company_gst.pdf",
            headers=Headers({"content-type": "application/pdf"}),
        )

        doc_gst = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            file=upload_file,
            document_type="GST_CERTIFICATE",
            tender_requirement_id=req_gst.id,
        )

        # Run Master Document Processing Pipeline
        proc_record = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_gst.id,
        )

        assert proc_record.extraction_method == ExtractionMethod.DIGITAL_PDF
        assert proc_record.processing_stage in [ProcessingStage.STRUCTURED_EXTRACTION, ProcessingStage.COMPLETED]
        assert proc_record.detected_document_type == DocumentClass.GST_CERTIFICATE
        assert proc_record.classification_confidence >= 0.80
        assert proc_record.classification_method == "RULE_BASED"
        assert proc_record.classification_requires_review is False
        print("  [PASS] Digital PDF automatically extracted, classified, and advanced through pipeline.")

        # -------------------------------------------------------------------------
        # Test 7: OCR Preprocessing -> OCR Engine -> Classification Flow
        # -------------------------------------------------------------------------
        print("\n[Test 7] Testing Standalone Image OCR -> Classification flow...")
        pan_png_bytes = create_synthetic_text_image_bytes([
            "INCOME TAX DEPARTMENT",
            "GOVT. OF INDIA",
            "PERMANENT ACCOUNT NUMBER",
            "PAN: ABCDE1234F",
            "NAME: SURESH KUMAR",
        ])
        upload_img_file = UploadFile(
            file=io.BytesIO(pan_png_bytes),
            size=len(pan_png_bytes),
            filename="director_pan.png",
            headers=Headers({"content-type": "image/png"}),
        )

        doc_pan = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            file=upload_img_file,
            document_type="PAN",
            tender_requirement_id=None,
        )

        proc_img_record = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_pan.id,
        )

        assert proc_img_record.extraction_method == ExtractionMethod.OCR
        assert proc_img_record.processing_stage in [ProcessingStage.STRUCTURED_EXTRACTION, ProcessingStage.COMPLETED]
        assert proc_img_record.detected_document_type == DocumentClass.PAN
        print("  [PASS] Standalone Image extracted via OCR and classified as PAN.")

        # -------------------------------------------------------------------------
        # Test 8: Classification REST API Endpoint & Explainability
        # -------------------------------------------------------------------------
        print("\n[Test 8] Testing get_document_classification service & explainability...")
        class_dto = get_document_classification(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_gst.id,
        )
        assert class_dto.detected_document_type == DocumentClass.GST_CERTIFICATE
        assert class_dto.confidence_level == ClassificationConfidenceLevel.HIGH
        assert class_dto.classification_method == "RULE_BASED"
        assert len(class_dto.classification_reason) > 0
        print("  [PASS] Classification DTO returned expected fields and explainability reason.")

        # -------------------------------------------------------------------------
        # Test 9: Strict Tenant Isolation on Classification Service
        # -------------------------------------------------------------------------
        print("\n[Test 9] Testing strict tenant isolation on classification service...")
        if user2:
            try:
                get_document_classification(
                    db=db,
                    current_user=user2,
                    bid_id=bid1.id,
                    document_id=doc_gst.id,
                )
                assert False, "Expected HTTPException 404 for cross-tenant access"
            except HTTPException as he:
                assert he.status_code == 404
                print("  [PASS] Cross-tenant classification inspection safely rejected with HTTP 404.")
        else:
            print("  [SKIP] Bidder 2 not available for tenant test.")

        # -------------------------------------------------------------------------
        # Test 10: Replaced Documents — Independent Classification Lifecycle
        # -------------------------------------------------------------------------
        print("\n[Test 10] Testing document replacement and independent classification...")
        oem_pdf_bytes = create_synthetic_pdf(oem_sample)
        replace_file = UploadFile(
            file=io.BytesIO(oem_pdf_bytes),
            size=len(oem_pdf_bytes),
            filename="cisco_oem_v2.pdf",
            headers=Headers({"content-type": "application/pdf"}),
        )

        new_doc = replace_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_gst.id,
            file=replace_file,
        )

        # Process new document version
        proc_v2_record = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=new_doc.id,
        )

        assert proc_v2_record.detected_document_type == DocumentClass.OEM_AUTHORIZATION
        # Note: Since the requirement was GST but replaced file is OEM, review should be flagged!
        assert proc_v2_record.classification_requires_review is True
        print("  [PASS] Replaced document classified independently and discrepancy review flagged.")

        print("\n" + "=" * 80)
        print("ALL 10/10 PART 4D INTEGRATION TESTS PASSED (100% SUCCESS)")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    run_tests()
