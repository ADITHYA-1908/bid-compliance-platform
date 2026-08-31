"""
Test Suite for Part 4E: Structured Entity / Field Extraction
Tests deterministic, regex- and label-based extraction across GST, PAN, Udyam, OEM,
Turnover, Financials, Experience, Local Content, Blacklist declarations, Conflicting Values,
Missing Fields, Master Pipeline Integration, and Tenant Security.
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
from app.services.structured_extraction_service import (
    extract_structured_entities_from_text,
    normalize_date_string,
    parse_indian_currency_to_number,
)
from app.services.bid_document_service import upload_bid_document
from app.services.document_processing_service import (
    execute_document_processing_pipeline,
    get_document_extracted_data,
    get_document_extracted_text,
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
    print("BIDVERIFY AI — PART 4E STRUCTURED ENTITY EXTRACTION TEST SUITE")
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
            name=f"Test Part4E Org 1 - {uuid.uuid4().hex[:6]}",
            organization_type="PRIVATE_LIMITED",
            registration_number=f"REG-4E-{uuid.uuid4().hex[:6]}",
            is_active=True,
        )
        db.add(org1)
        db.commit()
        db.refresh(org1)

        profile1 = Profile(
            organization_id=org1.id,
            role_id=bidder_role.id,
            full_name="Bidder One P4E",
            email=f"bidder1_p4e_{uuid.uuid4().hex[:6]}@example.com",
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

        # Bidder 2 Setup (for cross-tenant security checks)
        org2 = Organization(
            name=f"Test Part4E Org 2 - {uuid.uuid4().hex[:6]}",
            organization_type="PRIVATE_LIMITED",
            is_active=True,
        )
        db.add(org2)
        db.commit()
        db.refresh(org2)

        profile2 = Profile(
            organization_id=org2.id,
            role_id=bidder_role.id,
            full_name="Bidder Two P4E",
            email=f"bidder2_p4e_{uuid.uuid4().hex[:6]}@example.com",
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
            tender_number=f"GEM/2026/B/P4E-{uuid.uuid4().hex[:6]}",
            title="Part 4E Structured Entity Extraction Tender",
            description="Testing structured entity extraction across all document types",
            status="OPEN",
            submission_start_date=datetime.now(timezone.utc) - timedelta(days=1),
            submission_end_date=datetime.now(timezone.utc) + timedelta(days=30),
            estimated_value=8500000.0,
            currency="INR",
            organization_id=org1.id,
            created_by_profile_id=profile1.id,
        )
        db.add(tender)
        db.commit()
        db.refresh(tender)

        req_gst = TenderRequirement(
            tender_id=tender.id,
            code="REQ-GST-4E",
            name="GST Registration Certificate",
            category="STATUTORY",
            requirement_type="DOCUMENT",
            is_mandatory=True,
            is_active=True,
        )
        db.add(req_gst)
        db.commit()

        bid1 = Bid(
            tender_id=tender.id,
            bidder_organization_id=org1.id,
            created_by_profile_id=profile1.id,
            bid_number=f"BID-P4E-{uuid.uuid4().hex[:6]}",
            status="DRAFT",
            quoted_amount=8200000.0,
            currency="INR",
        )
        db.add(bid1)
        db.commit()
        db.refresh(bid1)

        print("  [PASS] Setup completed successfully.")

        # -------------------------------------------------------------------------
        # Test 1: Date & Currency Normalization Utilities
        # -------------------------------------------------------------------------
        print("\n[Test 1] Testing Date and Indian Currency normalization utilities...")
        assert normalize_date_string("15/08/2024") == "2024-08-15"
        assert normalize_date_string("2025-01-10") == "2025-01-10"
        assert normalize_date_string("31st March 2025") == "2025-03-31"

        assert parse_indian_currency_to_number("Rs. 5,00,00,000") == 50000000.0
        assert parse_indian_currency_to_number("5 Crore") == 50000000.0
        assert parse_indian_currency_to_number("5.26 Crores") == 52600000.0
        assert parse_indian_currency_to_number("45 Lakhs") == 4500000.0
        assert parse_indian_currency_to_number("Rs. 85,00,000") == 8500000.0
        print("  [PASS] Dates and Indian currency (Crores, Lakhs, commas) normalized accurately.")

        # -------------------------------------------------------------------------
        # Test 2: GST Certificate Structured Extraction
        # -------------------------------------------------------------------------
        print("\n[Test 2] Testing GST Certificate structured entity extraction...")
        gst_text = (
            "Government of India\n"
            "Form GST REG-06\n"
            "Registration Certificate\n"
            "Registration Number: 33ABCDE1234F1Z5\n"
            "Legal Name: Acme Tech Solutions Private Limited\n"
            "Trade Name: Acme Technologies\n"
            "Constitution of Business: Private Limited Company\n"
            "Date of Registration: 10/01/2024\n"
            "Address of Principal Place: No 42 Anna Salai, Chennai, Tamil Nadu 600002\n"
        )
        res_gst = extract_structured_entities_from_text(gst_text, DocumentClass.GST_CERTIFICATE)
        assert res_gst.document_type == DocumentClass.GST_CERTIFICATE
        assert res_gst.fields["gstin"].value == "33ABCDE1234F1Z5"
        assert res_gst.fields["gstin"].confidence >= 0.90
        assert res_gst.fields["legal_name"].value == "Acme Tech Solutions Private Limited"
        assert res_gst.fields["trade_name"].value == "Acme Technologies"
        assert res_gst.fields["constitution_of_business"].value == "Private Limited Company"
        assert res_gst.fields["registration_date"].value == "2024-01-10"
        assert res_gst.fields["state"].value == "Tamil Nadu"
        assert "Anna Salai" in res_gst.fields["principal_place_of_business"].value
        assert res_gst.requires_review is False
        print("  [PASS] GSTIN, Legal Name, Trade Name, Date, and State cleanly extracted.")

        # -------------------------------------------------------------------------
        # Test 3: PAN Card Structured Extraction
        # -------------------------------------------------------------------------
        print("\n[Test 3] Testing PAN Card structured entity extraction...")
        pan_text = (
            "INCOME TAX DEPARTMENT\n"
            "GOVT. OF INDIA\n"
            "Permanent Account Number Card\n"
            "PAN: ABCDE1234F\n"
            "Name: RAJESH KUMAR SHARMA\n"
            "Father's Name: SURESH KUMAR SHARMA\n"
            "Date of Birth: 15/08/1985\n"
        )
        res_pan = extract_structured_entities_from_text(pan_text, DocumentClass.PAN)
        assert res_pan.document_type == DocumentClass.PAN
        assert res_pan.fields["pan_number"].value == "ABCDE1234F"
        assert res_pan.fields["name"].value == "RAJESH KUMAR SHARMA"
        assert res_pan.fields["father_name"].value == "SURESH KUMAR SHARMA"
        assert res_pan.fields["date_of_birth"].value == "1985-08-15"
        assert res_pan.requires_review is False
        print("  [PASS] PAN number, Cardholder Name, Father Name, and DOB extracted.")

        # -------------------------------------------------------------------------
        # Test 4: Udyam Certificate Structured Extraction
        # -------------------------------------------------------------------------
        print("\n[Test 4] Testing Udyam Certificate structured entity extraction...")
        udyam_text = (
            "Ministry of Micro, Small and Medium Enterprises\n"
            "UDYAM REGISTRATION CERTIFICATE\n"
            "UDYAM REGISTRATION NUMBER: UDYAM-TN-00-1234567\n"
            "NAME OF ENTERPRISE: TECH FLOW SYSTEMS PRIVATE LIMITED\n"
            "MAJOR ACTIVITY: MANUFACTURING\n"
            "ENTERPRISE TYPE: MICRO\n"
            "DATE OF UDYAM REGISTRATION: 05/04/2023\n"
            "OFFICIAL ADDRESS OF ENTERPRISE: Plot 12 SIDCO Industrial Estate, Guindy, Chennai\n"
        )
        res_udyam = extract_structured_entities_from_text(udyam_text, DocumentClass.UDYAM_CERTIFICATE)
        assert res_udyam.fields["udyam_registration_number"].value == "UDYAM-TN-00-1234567"
        assert res_udyam.fields["enterprise_name"].value == "TECH FLOW SYSTEMS PRIVATE LIMITED"
        assert res_udyam.fields["enterprise_classification"].value == "MICRO"
        assert res_udyam.fields["major_activity"].value == "MANUFACTURING"
        assert res_udyam.fields["registration_date"].value == "2023-04-05"
        assert res_udyam.requires_review is False
        print("  [PASS] Udyam number, Enterprise Name, Classification (MICRO), and Activity extracted.")

        # -------------------------------------------------------------------------
        # Test 5: Turnover & Financial Statement Extraction (Crores / UDIN)
        # -------------------------------------------------------------------------
        print("\n[Test 5] Testing Turnover Certificate and Financial Statement extraction...")
        to_text = (
            "CA CERTIFICATE OF ANNUAL TURNOVER\n"
            "This is to certify that M/s Apex Cybernetics Enterprise has achieved the following Annual Gross Turnover:\n"
            "FY 2022-23: Rs. 4,50,00,000\n"
            "FY 2023-24: Rs. 5,20,00,000\n"
            "FY 2024-25: Rs. 6,10,00,000\n"
            "Average Annual Turnover: Rs. 5.26 Crores\n"
            "Chartered Accountant: R. Swaminathan and Associates\n"
            "Membership No: 123456\n"
            "UDIN: 24123456AAAAAB1234\n"
            "Date: 12/05/2025\n"
        )
        res_to = extract_structured_entities_from_text(to_text, DocumentClass.TURNOVER_CERTIFICATE)
        assert "annual_turnover_values" in res_to.fields
        to_values = res_to.fields["annual_turnover_values"].value
        assert to_values.get("2022-23") == 45000000.0
        assert to_values.get("2023-24") == 52000000.0
        assert to_values.get("2024-25") == 61000000.0
        assert res_to.fields["average_annual_turnover"].value == 52600000.0
        assert res_to.fields["udin"].value == "24123456AAAAAB1234"
        assert res_to.fields["membership_number"].value == "123456"
        print("  [PASS] Turnover FY breakdown, Average (5.26 Cr -> 52.6M), UDIN, and CA details extracted.")

        # -------------------------------------------------------------------------
        # Test 6: OEM, Experience, Local Content & Blacklist Extraction
        # -------------------------------------------------------------------------
        print("\n[Test 6] Testing OEM, Experience, Local Content, and Blacklist Undertaking extraction...")
        oem_text = (
            "MANUFACTURERS AUTHORIZATION FORM (MAF)\n"
            "Ref: OEM/AUTH/2026/08\n"
            "We, Cisco Systems Inc, Original Equipment Manufacturer of networking products,\n"
            "hereby authorize M/s Acme Solutions as our Authorized Partner\n"
            "for Tender GEM/2026/B/88991.\n"
            "Date: 2026-08-20\n"
            "Authorized Signatory: John Doe\n"
        )
        res_oem = extract_structured_entities_from_text(oem_text, DocumentClass.OEM_AUTHORIZATION)
        assert "Cisco Systems Inc" in res_oem.fields["oem_name"].value
        assert "Acme Solutions" in res_oem.fields["authorized_entity"].value
        assert res_oem.fields["reference_number"].value == "OEM/AUTH/2026/08"

        mii_text = (
            "LOCAL CONTENT DECLARATION (MAKE IN INDIA)\n"
            "We hereby declare that our offered product meets Class-I Local Supplier requirements.\n"
            "Percentage of Local Content is 65%.\n"
            "Date: 15/07/2025\n"
        )
        res_mii = extract_structured_entities_from_text(mii_text, DocumentClass.LOCAL_CONTENT_DECLARATION)
        assert res_mii.fields["local_content_percentage"].value == 65.0
        assert res_mii.fields["supplier_class"].value == "Class-I Local Supplier"

        bl_text = (
            "NON-BLACKLISTING UNDERTAKING\n"
            "We hereby affirm that M/s Apex Infra has not been blacklisted or debarred by any Govt PSU.\n"
            "Date: 2026-08-25\n"
        )
        res_bl = extract_structured_entities_from_text(bl_text, DocumentClass.BLACKLIST_DECLARATION)
        assert res_bl.fields["blacklisted_status_claim"].value is False  # Declares NOT blacklisted
        assert res_bl.fields["debarred_status_claim"].value is False
        print("  [PASS] OEM scope, 65% Local Content, and False blacklisted claim successfully parsed.")

        # -------------------------------------------------------------------------
        # Test 7: Conflict Detection (Multiple Conflicting Values)
        # -------------------------------------------------------------------------
        print("\n[Test 7] Testing conflict detection on multiple conflicting identifiers...")
        conflict_text = (
            "--- Page 1 ---\n"
            "GST Registration Certificate\n"
            "GSTIN: 33ABCDE1234F1Z5\n"
            "Legal Name: Alpha Tech Ltd\n"
            "--- Page 2 ---\n"
            "Amended GSTIN: 27XYZPQ9876R1Z9\n"
        )
        res_conf = extract_structured_entities_from_text(conflict_text, DocumentClass.GST_CERTIFICATE)
        assert res_conf.fields["gstin"].is_conflict is True
        assert res_conf.requires_review is True
        assert any("conflicting GSTIN" in r for r in res_conf.review_reasons)
        print("  [PASS] Multiple conflicting GSTINs flagged with is_conflict=True and requires_review=True.")

        # -------------------------------------------------------------------------
        # Test 8: Missing Non-Mandatory Fields (Graceful Partial Extraction)
        # -------------------------------------------------------------------------
        print("\n[Test 8] Testing graceful partial extraction when optional fields are missing...")
        partial_gst = (
            "Form GST REG-06\n"
            "Registration Number: 33ABCDE1234F1Z5\n"
            "Legal Name: Partial Extractor Pvt Ltd\n"
            "(No registration date or trade name mentioned)\n"
        )
        res_partial = extract_structured_entities_from_text(partial_gst, DocumentClass.GST_CERTIFICATE)
        assert res_partial.fields["gstin"].value == "33ABCDE1234F1Z5"
        assert res_partial.fields["legal_name"].value == "Partial Extractor Pvt Ltd"
        assert "trade_name" not in res_partial.fields
        print("  [PASS] Present fields extracted cleanly without pipeline errors.")

        # -------------------------------------------------------------------------
        # Test 9: Full Pipeline Integration (PDF Ingestion -> Classification -> Structured Extraction)
        # -------------------------------------------------------------------------
        print("\n[Test 9] Testing End-to-End Pipeline Integration with DB persistence...")
        pdf_bytes = create_synthetic_pdf(gst_text)
        upload_res = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            file=UploadFile(
                file=io.BytesIO(pdf_bytes),
                size=len(pdf_bytes),
                filename="gst_certificate_e2e.pdf",
                headers=Headers({"content-type": "application/pdf"}),
            ),
            document_type="GST_CERTIFICATE",
            tender_requirement_id=req_gst.id,
        )

        proc_record = execute_document_processing_pipeline(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_res.id,
        )

        assert proc_record.processing_stage == ProcessingStage.COMPLETED
        assert proc_record.processing_status == ProcessingStatus.COMPLETED
        assert proc_record.detected_document_type == DocumentClass.GST_CERTIFICATE
        assert proc_record.extracted_data is not None
        assert proc_record.extracted_data["fields"]["gstin"]["value"] == "33ABCDE1234F1Z5"
        assert proc_record.extraction_confidence >= 0.80
        assert proc_record.extraction_requires_review is False
        print("  [PASS] Full pipeline advanced to COMPLETED with persisted structured fields in PostgreSQL.")

        # -------------------------------------------------------------------------
        # Test 10: Tenant Isolation & SUBMITTED Bid Document Access
        # -------------------------------------------------------------------------
        print("\n[Test 10] Testing Tenant Isolation and SUBMITTED bid document access...")
        # Bidder 1 retrieves extracted structured data
        ext_data = get_document_extracted_data(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_res.id,
        )
        assert ext_data.document_type == DocumentClass.GST_CERTIFICATE
        assert ext_data.fields["gstin"].value == "33ABCDE1234F1Z5"
        assert ext_data.fields["gstin"].page == 1

        # Bidder 2 attempts cross-tenant access -> HTTP 404
        try:
            get_document_extracted_data(
                db=db,
                current_user=user2,
                bid_id=bid1.id,
                document_id=upload_res.id,
            )
            assert False, "Bidder 2 should be rejected with 404"
        except HTTPException as he:
            assert he.status_code == 404
            print("  [PASS] Cross-tenant structured data access safely rejected with HTTP 404.")

        # Mark bid as SUBMITTED and verify extracted data retrieval is still accessible
        bid1.status = "SUBMITTED"
        bid1.submitted_at = datetime.now(timezone.utc)
        db.commit()

        submitted_ext_data = get_document_extracted_data(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=upload_res.id,
        )
        assert submitted_ext_data.fields["gstin"].value == "33ABCDE1234F1Z5"
        print("  [PASS] Structured extracted data successfully accessible on SUBMITTED bids.")

        print("\n" + "=" * 80)
        print("ALL 10/10 PART 4E INTEGRATION TESTS PASSED (100% SUCCESS)")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    run_tests()
