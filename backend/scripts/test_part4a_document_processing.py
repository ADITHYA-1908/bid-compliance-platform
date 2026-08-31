"""
Part 4A Master Integration & Regression Test Suite
Tests Document Ingestion & Processing Foundation:
- DocumentProcessing table, model, relationships, enums
- Automatic provisioning on upload & replacement
- Storage binary existence verification & error telemetry
- Lifecycle state transitions (QUEUED -> PROCESSING -> COMPLETED / FAILED)
- Retry workflow on failed documents
- Cross-tenant isolation & security
- Processing access on SUBMITTED bids
- Idempotent backfill verification
"""

import os
import sys
import io
import uuid
from datetime import datetime, timezone, timedelta

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import fitz
from fastapi import UploadFile
from sqlalchemy import select
from starlette.datastructures import Headers

from app.core.config import settings
from app.core.security import create_access_token
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
from app.services.bid_document_service import (
    upload_bid_document,
    replace_bid_document,
    remove_bid_document,
    list_bid_documents,
    get_bid_document,
)
from app.services.document_processing_service import (
    create_or_get_processing_record,
    get_document_processing,
    queue_document_processing,
    retry_document_processing,
    mark_processing_started,
    update_processing_stage,
    mark_processing_completed,
    mark_processing_failed,
    backfill_missing_processing_records,
)
from app.services.storage_service import storage_service
from fastapi import HTTPException


def run_tests():
    print("=" * 80)
    print("BIDVERIFY AI — PART 4A DOCUMENT INGESTION & PROCESSING TEST SUITE")
    print("=" * 80)

    session_factory = get_session_factory()
    db = session_factory()

    try:
        # ---------------------------------------------------------------------
        # Setup Test Fixtures: Roles, Users, Tenders, Requirements, Bids
        # ---------------------------------------------------------------------
        print("\n[Setup] Initializing test fixtures...")
        bidder_role = db.scalars(select(Role).where(Role.name == "BIDDER")).first()
        po_role = db.scalars(select(Role).where(Role.name == "PROCUREMENT_OFFICER")).first()

        # Bidder 1 Setup
        org1_name = f"Test Part4A Org 1 - {uuid.uuid4().hex[:6]}"
        org1 = Organization(
            name=org1_name,
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
            full_name="Bidder One P4A",
            email=f"bidder1_p4a_{uuid.uuid4().hex[:6]}@example.com",
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
            name=f"Test Part4A Org 2 - {uuid.uuid4().hex[:6]}",
            organization_type="PRIVATE_LIMITED",
            is_active=True,
        )
        db.add(org2)
        db.commit()
        db.refresh(org2)

        profile2 = Profile(
            organization_id=org2.id,
            role_id=bidder_role.id,
            full_name="Bidder Two P4A",
            email=f"bidder2_p4a_{uuid.uuid4().hex[:6]}@example.com",
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
            tender_number=f"GEM/2026/B/P4A-{uuid.uuid4().hex[:6]}",
            title="Part 4A Document Ingestion Validation Tender",
            description="Testing document ingestion and processing foundation",
            status="OPEN",
            submission_start_date=datetime.now(timezone.utc) - timedelta(days=1),
            submission_end_date=datetime.now(timezone.utc) + timedelta(days=30),
            estimated_value=2500000.0,
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
            name="GST Registration Certificate",
            requirement_type="DOCUMENT",
            is_mandatory=True,
            is_active=True,
        )
        req2 = TenderRequirement(
            tender_id=tender.id,
            code="DOC-REQ-002",
            name="OEM Authorization Letter",
            requirement_type="DOCUMENT",
            is_mandatory=False,
            is_active=True,
        )
        db.add_all([req1, req2])
        db.commit()

        # Bid for Bidder 1
        bid1 = Bid(
            tender_id=tender.id,
            bidder_organization_id=org1.id,
            created_by_profile_id=profile1.id,
            bid_number=f"BID-P4A-{uuid.uuid4().hex[:6]}",
            status="DRAFT",
            quoted_amount=2400000.0,
            currency="INR",
        )
        db.add(bid1)
        db.commit()
        db.refresh(bid1)

        print("  [PASS] Setup completed successfully.")

        # ---------------------------------------------------------------------
        # TEST 1: Model & Enum Integrity
        # ---------------------------------------------------------------------
        print("\n[Test 1] Verifying DocumentProcessing model, fields, and enums...")
        assert "QUEUED" in ProcessingStatus.ALL
        assert "PROCESSING" in ProcessingStatus.ALL
        assert "COMPLETED" in ProcessingStatus.ALL
        assert "FAILED" in ProcessingStatus.ALL
        assert "NEEDS_REVIEW" in ProcessingStatus.ALL

        assert "INGESTION" in ProcessingStage.ALL
        assert "TEXT_EXTRACTION" in ProcessingStage.ALL
        assert "OCR" in ProcessingStage.ALL
        assert "CLASSIFICATION" in ProcessingStage.ALL
        assert "STRUCTURED_EXTRACTION" in ProcessingStage.ALL
        assert "COMPLETED" in ProcessingStage.ALL

        assert "NONE" in ExtractionMethod.ALL
        assert "DIGITAL_PDF" in ExtractionMethod.ALL
        assert "OCR" in ExtractionMethod.ALL
        assert "HYBRID" in ExtractionMethod.ALL
        print("  [PASS] Enums verified.")

        # ---------------------------------------------------------------------
        # TEST 2: Automatic Creation of DocumentProcessing on Upload
        # ---------------------------------------------------------------------
        print("\n[Test 2] Testing automatic DocumentProcessing provisioning on document upload...")
        doc_pdf = fitz.open()
        p = doc_pdf.new_page()
        p.insert_text((50, 72), "GST Registration Certificate Sample for Part 4A Testing with sufficient text content", fontsize=11)
        sample_pdf_bytes = doc_pdf.tobytes()
        doc_pdf.close()
        file_obj = io.BytesIO(sample_pdf_bytes)
        upload_file = UploadFile(
            file=file_obj,
            size=len(sample_pdf_bytes),
            filename="gst_certificate.pdf",
            headers=Headers({"content-type": "application/pdf"}),
        )

        doc_res = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            file=upload_file,
            document_type="GST_CERTIFICATE",
            tender_requirement_id=req1.id,
            notes="Uploaded for Part 4A test",
        )

        assert doc_res is not None
        assert doc_res.processing is not None
        assert doc_res.processing.processing_status == ProcessingStatus.QUEUED
        assert doc_res.processing.processing_stage == ProcessingStage.INGESTION
        assert doc_res.processing.extraction_method == ExtractionMethod.NONE
        assert doc_res.processing.raw_text is None
        assert doc_res.processing.normalized_text is None
        assert doc_res.processing.error_code is None
        print(f"  [PASS] BidDocument {doc_res.id} auto-provisioned DocumentProcessing record in QUEUED status.")

        # ---------------------------------------------------------------------
        # TEST 3: State Transitions & Execution Telemetry Helpers
        # ---------------------------------------------------------------------
        print("\n[Test 3] Testing processing state transitions and timestamp tracking...")
        proc_id = doc_res.processing.id
        started = mark_processing_started(db, proc_id, stage=ProcessingStage.TEXT_EXTRACTION)
        assert started.processing_status == ProcessingStatus.PROCESSING
        assert started.processing_stage == ProcessingStage.TEXT_EXTRACTION
        assert started.processing_started_at is not None
        print("  [PASS] Transition to PROCESSING + TEXT_EXTRACTION succeeded.")

        updated = update_processing_stage(db, doc_res.processing.id, stage=ProcessingStage.OCR, extraction_method=ExtractionMethod.OCR)
        assert updated.processing_stage == ProcessingStage.OCR
        assert updated.extraction_method == ExtractionMethod.OCR
        print("  [PASS] Stage update to OCR + OCR method succeeded.")

        completed = mark_processing_completed(db, doc_res.processing.id, page_count=2, raw_text="Extracted text sample", normalized_text="Extracted text sample")
        assert completed.processing_status == ProcessingStatus.COMPLETED
        assert completed.processing_stage == ProcessingStage.COMPLETED
        assert completed.processing_completed_at is not None
        assert completed.page_count == 2
        print("  [PASS] Transition to COMPLETED with page_count=2 and timestamp succeeded.")

        failed = mark_processing_failed(db, doc_res.processing.id, error_code="TEST_ERROR", error_message="Simulated error for testing")
        assert failed.processing_status == ProcessingStatus.FAILED
        assert failed.error_code == "TEST_ERROR"
        assert failed.error_message == "Simulated error for testing"
        print("  [PASS] Transition to FAILED with error telemetry succeeded.")

        # ---------------------------------------------------------------------
        # TEST 4: Retry Workflow for Failed Jobs
        # ---------------------------------------------------------------------
        print("\n[Test 4] Testing retry workflow on failed document processing...")
        retried_proc = retry_document_processing(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_res.id,
        )
        assert retried_proc.processing_status in [
            ProcessingStatus.QUEUED,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.COMPLETED,
            ProcessingStatus.NEEDS_REVIEW,
        ]
        print("  [PASS] Retry successfully reset FAILED job back to active processing.")

        # Verify retry on COMPLETED job is rejected
        proc_db = db.scalars(select(DocumentProcessing).where(DocumentProcessing.bid_document_id == doc_res.id)).first()
        proc_db.processing_status = ProcessingStatus.COMPLETED
        db.commit()
        try:
            retry_document_processing(
                db=db,
                current_user=user1,
                bid_id=bid1.id,
                document_id=doc_res.id,
            )
            assert False, "Should have failed to retry a COMPLETED job"
        except HTTPException as he:
            assert he.status_code == 400
            print("  [PASS] Non-failed job retry correctly rejected with HTTP 400.")

        # ---------------------------------------------------------------------
        # TEST 5: Storage Existence Verification & Failure Handling
        # ---------------------------------------------------------------------
        print("\n[Test 5] Testing storage file existence verification & failure handling...")
        # Create a document whose storage path points to a non-existent file
        ghost_doc = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid1.id,
            uploaded_by_profile_id=profile1.id,
            document_type="TECHNICAL_DOCUMENT",
            document_name="Ghost File",
            original_filename="ghost.pdf",
            storage_path="bids/non_existent/ghost.pdf",
            mime_type="application/pdf",
            file_size=1024,
            status="UPLOADED",
            is_active=True,
        )
        db.add(ghost_doc)
        db.commit()

        try:
            queue_document_processing(
                db=db,
                current_user=user1,
                bid_id=bid1.id,
                document_id=ghost_doc.id,
            )
            assert False, "Should have failed due to missing storage file"
        except HTTPException as he:
            assert he.status_code == 404
            # Verify failure telemetry was persisted in DB
            db.expire_all()
            ghost_proc = db.scalars(select(DocumentProcessing).where(DocumentProcessing.bid_document_id == ghost_doc.id)).one()
            assert ghost_proc.processing_status == ProcessingStatus.FAILED
            assert ghost_proc.error_code == "FILE_NOT_FOUND"
            print("  [PASS] Missing storage file correctly recorded failure telemetry and raised HTTP 404.")

        # ---------------------------------------------------------------------
        # TEST 6: Preservation of Processing History on Replacement
        # ---------------------------------------------------------------------
        print("\n[Test 6] Testing document replacement history preservation...")
        new_pdf_bytes = b"%PDF-1.4 updated gst certificate v2 content"
        file_obj2 = io.BytesIO(new_pdf_bytes)
        upload_file2 = UploadFile(
            file=file_obj2,
            size=len(new_pdf_bytes),
            filename="gst_certificate_v2.pdf",
            headers=Headers({"content-type": "application/pdf"}),
        )

        replaced_res = replace_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc_res.id,
            file=upload_file2,
            notes="Version 2 replacement",
        )

        assert replaced_res.version == 2
        assert replaced_res.processing is not None
        assert replaced_res.processing.processing_status == ProcessingStatus.QUEUED
        assert replaced_res.processing.bid_document_id == replaced_res.id

        # Verify old doc (v1) still has its processing record intact
        db.expire_all()
        old_proc = db.scalars(select(DocumentProcessing).where(DocumentProcessing.bid_document_id == doc_res.id)).first()
        assert old_proc is not None
        assert old_proc.id == proc_id
        print("  [PASS] Document replacement preserved v1 processing history and created fresh v2 processing record.")

        # ---------------------------------------------------------------------
        # TEST 7: Preservation of Processing History on Soft Removal
        # ---------------------------------------------------------------------
        print("\n[Test 7] Testing document soft-removal history preservation...")
        # Upload another document to remove
        doc3_bytes = b"%PDF-1.4 authorization letter"
        doc3_res = upload_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            file=UploadFile(file=io.BytesIO(doc3_bytes), size=len(doc3_bytes), filename="oem_auth.pdf"),
            document_type="OEM_AUTHORIZATION",
            tender_requirement_id=req2.id,
        )
        doc3_proc_id = doc3_res.processing.id

        removed_doc = remove_bid_document(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=doc3_res.id,
        )
        assert removed_doc.is_active is False
        assert removed_doc.status == "REMOVED"

        # Verify DocumentProcessing is preserved for audit
        db.expire_all()
        preserved_proc = db.scalars(select(DocumentProcessing).where(DocumentProcessing.bid_document_id == doc3_res.id)).first()
        assert preserved_proc is not None
        assert preserved_proc.id == doc3_proc_id
        print("  [PASS] Soft-removed document preserved DocumentProcessing audit record.")

        # ---------------------------------------------------------------------
        # TEST 8: Cross-Tenant Security & Tenant Isolation
        # ---------------------------------------------------------------------
        print("\n[Test 8] Testing cross-tenant isolation and security...")
        # Bidder 2 attempts to view or process Bidder 1's document -> 404
        try:
            get_document_processing(
                db=db,
                current_user=user2,
                bid_id=bid1.id,
                document_id=replaced_res.id,
            )
            assert False, "Bidder 2 should not be able to access Bidder 1 document"
        except HTTPException as he:
            assert he.status_code == 404
            print("  [PASS] Cross-tenant GET processing access safely rejected with HTTP 404.")

        try:
            queue_document_processing(
                db=db,
                current_user=user2,
                bid_id=bid1.id,
                document_id=replaced_res.id,
            )
            assert False, "Bidder 2 should not be able to trigger processing on Bidder 1 document"
        except HTTPException as he:
            assert he.status_code == 404
            print("  [PASS] Cross-tenant POST process trigger safely rejected with HTTP 404.")

        # ---------------------------------------------------------------------
        # TEST 9: Processing Permitted on SUBMITTED Bids
        # ---------------------------------------------------------------------
        print("\n[Test 9] Testing document processing on SUBMITTED bids...")
        bid1.status = "SUBMITTED"
        bid1.submitted_at = datetime.now(timezone.utc)
        db.commit()

        # Reading and Queueing processing on submitted bid must succeed
        submitted_proc = get_document_processing(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=replaced_res.id,
        )
        assert submitted_proc is not None
        assert submitted_proc.bid_document_id == replaced_res.id

        queue_submitted = queue_document_processing(
            db=db,
            current_user=user1,
            bid_id=bid1.id,
            document_id=replaced_res.id,
        )
        assert queue_submitted is not None
        print("  [PASS] Document processing inspection and queueing verified on SUBMITTED bids.")

        # ---------------------------------------------------------------------
        # TEST 10: Idempotent Backfill Verification
        # ---------------------------------------------------------------------
        print("\n[Test 10] Testing idempotent backfill logic...")
        backfilled_count = backfill_missing_processing_records(db)
        assert backfilled_count == 0, f"Expected 0 missing records to backfill, got {backfilled_count}"
        print("  [PASS] Idempotent backfill verified (0 missing records on fully-provisioned system).")

        print("\n" + "=" * 80)
        print("ALL 10/10 PART 4A INTEGRATION TESTS PASSED (100% SUCCESS)")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    run_tests()
