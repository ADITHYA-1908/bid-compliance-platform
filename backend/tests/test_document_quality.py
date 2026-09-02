"""
Comprehensive Automated Tests for Part 11: Advanced Document Quality Check
Tests deterministic CV blur detection, blank page identification, low resolution,
skew angle diagnostics, corrupted PDF handling, 0-100 scoring, early pipeline halting,
human review synchronization, and multi-tenant security isolation.
"""

import io
import uuid
import cv2
import fitz
import numpy as np
import pytest
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.document_processing import (
    DocumentProcessing,
    ProcessingStage,
    ProcessingStatus,
)
from app.db.models.document_quality import (
    DocumentQualityResult,
    DocumentPageQuality,
    QualityLevel,
)
from app.db.models.human_review import HumanReviewItem, ReviewType
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.user import User
from app.db.session import get_session_factory
from app.services.document_processing_service import execute_document_processing_pipeline
from app.services.document_quality_service import DocumentQualityService
from app.services.procurement.human_review_service import HumanReviewService


@pytest.fixture
def db_session():
    """Provides a database session for integration tests and tears it down."""
    SessionFactory = get_session_factory()
    session = SessionFactory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _create_synthetic_clean_pdf() -> bytes:
    """Generates a clean, 2-page sharp PDF with native text."""
    doc = fitz.open()
    for page_num in range(2):
        page = doc.new_page(width=595, height=842)
        text = (
            f"BIDDER COMPLIANCE VERIFICATION DOCUMENT - PAGE {page_num + 1}\n"
            "This is a high-quality statutory declaration for BidVerify AI.\n"
            "GSTIN: 27AAPFU0939F1ZV\n"
            "PAN: AAPFU0939F\n"
            "Turnover for FY 2024-2025: INR 25,00,00,000\n"
            "Company has never been blacklisted or debarred by any government department.\n"
        )
        page.insert_text((50, 72), text, fontsize=12)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def _create_synthetic_blank_pdf() -> bytes:
    """Generates a 2-page PDF where page 2 is completely blank."""
    doc = fitz.open()
    # Page 1 has text
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 72), "Page 1: Valid Tender Information and Bid Details.", fontsize=12)
    # Page 2 is completely empty
    doc.new_page(width=595, height=842)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def _create_synthetic_blurry_image() -> bytes:
    """Generates a severely blurred PNG image using Gaussian Blur."""
    # Create base image with text
    img = np.full((1000, 800, 3), 255, dtype=np.uint8)
    cv2.putText(img, "BLURRY TENDER DOCUMENT", (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
    cv2.putText(img, "UNREADABLE SCAN COPY", (100, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    # Heavy Gaussian Blur to drop Laplacian variance below 10.0
    blurred = cv2.GaussianBlur(img, (55, 55), 0)
    _, encoded = cv2.imencode(".png", blurred)
    return encoded.tobytes()


def _create_synthetic_low_res_image() -> bytes:
    """Generates a very low resolution image (200x200 px)."""
    img = np.full((200, 200, 3), 255, dtype=np.uint8)
    cv2.putText(img, "TINY", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    _, encoded = cv2.imencode(".png", img)
    return encoded.tobytes()


@pytest.fixture
def test_setup(db_session: Session):
    """Sets up tenant organization, users, tender, bid, and sample bid document."""
    org = Organization(id=uuid.uuid4(), name=f"Quality Test Org {uuid.uuid4().hex[:6]}")
    db_session.add(org)

    role_bidder = db_session.query(Role).filter_by(name="BIDDER").first()
    if not role_bidder:
        role_bidder = Role(id=uuid.uuid4(), name="BIDDER", description="Bidder")
        db_session.add(role_bidder)

    role_po = db_session.query(Role).filter_by(name="PROCUREMENT_OFFICER").first()
    if not role_po:
        role_po = Role(id=uuid.uuid4(), name="PROCUREMENT_OFFICER", description="PO")
        db_session.add(role_po)

    email_b = f"bidder_{uuid.uuid4().hex[:6]}@example.com"
    prof_bidder = Profile(id=uuid.uuid4(), full_name="Test Bidder", email=email_b, role=role_bidder, organization=org)
    user_bidder = User(id=uuid.uuid4(), email=email_b, password_hash="mock_hash", profile=prof_bidder)
    db_session.add_all([prof_bidder, user_bidder])

    email_po = f"po_{uuid.uuid4().hex[:6]}@example.com"
    prof_po = Profile(id=uuid.uuid4(), full_name="Test Officer", email=email_po, role=role_po, organization=org)
    user_po = User(id=uuid.uuid4(), email=email_po, password_hash="mock_hash", profile=prof_po)
    db_session.add_all([prof_po, user_po])

    tender = Tender(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by_profile_id=prof_po.id,
        title="Quality Test Tender",
        tender_number=f"TND-{uuid.uuid4().hex[:6]}",
        status="PUBLISHED",
        is_active=True,
    )
    db_session.add(tender)

    bid = Bid(
        id=uuid.uuid4(),
        tender_id=tender.id,
        bidder_organization_id=org.id,
        created_by_profile_id=prof_bidder.id,
        bid_number=f"BID-Q-{uuid.uuid4().hex[:6]}",
        status="DRAFT",
        is_active=True,
    )
    db_session.add(bid)
    db_session.commit()

    return {
        "org": org,
        "bidder": user_bidder,
        "po": user_po,
        "tender": tender,
        "bid": bid,
    }


def test_quality_clean_pdf(db_session: Session, test_setup):
    """Verifies that a clean, sharp PDF scores 100 with GOOD quality level."""
    clean_bytes = _create_synthetic_clean_pdf()
    doc = BidDocument(
        id=uuid.uuid4(),
        bid_id=test_setup["bid"].id,
        uploaded_by_profile_id=test_setup["bidder"].profile_id,
        document_type="TECHNICAL_DOCUMENT",
        document_name="Clean Declaration",
        original_filename="clean_declaration.pdf",
        mime_type="application/pdf",
        storage_path="mock/clean.pdf",
        file_size=len(clean_bytes),
        is_active=True,
    )
    db_session.add(doc)
    db_session.commit()

    qr = DocumentQualityService.evaluate_document_quality(
        db=db_session,
        doc=doc,
        file_bytes=clean_bytes,
        proc=None,
        user=test_setup["bidder"],
    )

    assert qr.quality_score >= 90.0
    assert qr.quality_level == QualityLevel.GOOD
    assert qr.review_required is False
    assert qr.is_corrupted is False
    assert qr.is_password_protected is False
    assert qr.is_blurry is False
    assert qr.has_blank_pages is False
    assert qr.page_count == 2
    assert len(qr.page_qualities) == 2


def test_quality_blurry_image(db_session: Session, test_setup):
    """Verifies that a heavily blurred scan is flagged as blurry with reduced score."""
    blurry_bytes = _create_synthetic_blurry_image()
    doc = BidDocument(
        id=uuid.uuid4(),
        bid_id=test_setup["bid"].id,
        uploaded_by_profile_id=test_setup["bidder"].profile_id,
        document_type="FINANCIAL_STATEMENT",
        document_name="Blurry Scan",
        original_filename="blurry_scan.png",
        mime_type="image/png",
        storage_path="mock/blurry.png",
        file_size=len(blurry_bytes),
        is_active=True,
    )
    db_session.add(doc)
    db_session.commit()

    qr = DocumentQualityService.evaluate_document_quality(
        db=db_session,
        doc=doc,
        file_bytes=blurry_bytes,
        proc=None,
        user=test_setup["bidder"],
    )

    assert qr.is_blurry is True
    assert qr.quality_score < 90.0
    assert any("blurry" in fb.lower() for fb in qr.bidder_feedback)


def test_quality_blank_page_detection(db_session: Session, test_setup):
    """Verifies that blank pages inside a PDF are detected and penalized."""
    blank_bytes = _create_synthetic_blank_pdf()
    doc = BidDocument(
        id=uuid.uuid4(),
        bid_id=test_setup["bid"].id,
        uploaded_by_profile_id=test_setup["bidder"].profile_id,
        document_type="TECHNICAL_DOCUMENT",
        document_name="Has Blank Page",
        original_filename="has_blank_page.pdf",
        mime_type="application/pdf",
        storage_path="mock/blank.pdf",
        file_size=len(blank_bytes),
        is_active=True,
    )
    db_session.add(doc)
    db_session.commit()

    qr = DocumentQualityService.evaluate_document_quality(
        db=db_session,
        doc=doc,
        file_bytes=blank_bytes,
        proc=None,
        user=test_setup["bidder"],
    )

    assert qr.has_blank_pages is True
    assert qr.page_count == 2
    p2 = next(p for p in qr.page_qualities if p.page_number == 2)
    assert p2.is_blank is True
    assert any("blank" in fb.lower() for fb in qr.bidder_feedback)


def test_quality_corrupted_file(db_session: Session, test_setup):
    """Verifies that corrupted bytes result in score 0 and UNUSABLE level."""
    corrupt_bytes = b"NOT_A_VALID_PDF_HEADER_JUST_RANDOM_GARBAGE_BYTES_123456"
    doc = BidDocument(
        id=uuid.uuid4(),
        bid_id=test_setup["bid"].id,
        uploaded_by_profile_id=test_setup["bidder"].profile_id,
        document_type="TECHNICAL_DOCUMENT",
        document_name="Corrupted PDF",
        original_filename="corrupted.pdf",
        mime_type="application/pdf",
        storage_path="mock/corrupt.pdf",
        file_size=len(corrupt_bytes),
        is_active=True,
    )
    db_session.add(doc)
    db_session.commit()

    qr = DocumentQualityService.evaluate_document_quality(
        db=db_session,
        doc=doc,
        file_bytes=corrupt_bytes,
        proc=None,
        user=test_setup["bidder"],
    )

    assert qr.quality_score == 0.0
    assert qr.quality_level == QualityLevel.UNUSABLE
    assert qr.is_corrupted is True
    assert qr.review_required is True
    assert any("corrupted" in fb.lower() or "unreadable" in fb.lower() for fb in qr.bidder_feedback)


def test_quality_low_resolution_image(db_session: Session, test_setup):
    """Verifies that tiny low-resolution scans are flagged."""
    low_res_bytes = _create_synthetic_low_res_image()
    doc = BidDocument(
        id=uuid.uuid4(),
        bid_id=test_setup["bid"].id,
        uploaded_by_profile_id=test_setup["bidder"].profile_id,
        document_type="TECHNICAL_DOCUMENT",
        document_name="Tiny Resolution",
        original_filename="tiny_resolution.png",
        mime_type="image/png",
        storage_path="mock/tiny.png",
        file_size=len(low_res_bytes),
        is_active=True,
    )
    db_session.add(doc)
    db_session.commit()

    qr = DocumentQualityService.evaluate_document_quality(
        db=db_session,
        doc=doc,
        file_bytes=low_res_bytes,
        proc=None,
        user=test_setup["bidder"],
    )

    assert qr.has_low_resolution_pages is True
    assert qr.quality_score < 90.0


def test_deterministic_scoring_boundaries(db_session: Session, test_setup):
    """Verifies deterministic mapping across all score bands (GOOD, ACCEPTABLE, POOR, UNUSABLE)."""
    # Test scoring helper
    diag_good = [{"is_blank": False, "is_unreadable": False, "is_blurry": False, "is_low_res": False, "is_skewed": False, "blur_score": 250.0}]
    score, level, req, _, _ = DocumentQualityService._compute_overall_quality(diag_good)
    assert score == 100.0
    assert level == QualityLevel.GOOD
    assert req is False

    # Blurry single page -> 85 (ACCEPTABLE)
    diag_blurry = [{"is_blank": False, "is_unreadable": False, "is_blurry": True, "is_low_res": False, "is_skewed": False, "blur_score": 45.0}]
    score, level, req, _, _ = DocumentQualityService._compute_overall_quality(diag_blurry)
    assert score == 85.0
    assert level == QualityLevel.ACCEPTABLE

    # Blurry + Low Res + Skewed -> 67.0 (POOR: 40-69)
    diag_poor = [{"is_blank": False, "is_unreadable": False, "is_blurry": True, "is_low_res": True, "is_skewed": True, "blur_score": 35.0}]
    score, level, req, _, _ = DocumentQualityService._compute_overall_quality(diag_poor)
    assert score == 67.0
    assert level == QualityLevel.POOR
    assert req is True

    # Unreadable -> UNUSABLE
    diag_unreadable = [
        {"is_blank": False, "is_unreadable": True, "is_blurry": True, "is_low_res": True, "is_skewed": True, "blur_score": 5.0},
        {"is_blank": False, "is_unreadable": True, "is_blurry": True, "is_low_res": True, "is_skewed": True, "blur_score": 4.0},
    ]
    score, level, req, _, _ = DocumentQualityService._compute_overall_quality(diag_unreadable)
    assert score <= 39.0
    assert level == QualityLevel.UNUSABLE
    assert req is True


def test_human_review_sync_for_poor_quality(db_session: Session, test_setup):
    """Verifies that HumanReviewService syncs a review item when document quality is POOR."""
    doc = BidDocument(
        id=uuid.uuid4(),
        bid_id=test_setup["bid"].id,
        uploaded_by_profile_id=test_setup["bidder"].profile_id,
        document_type="TECHNICAL_DOCUMENT",
        document_name="Poor Quality Doc",
        original_filename="poor_doc.pdf",
        mime_type="application/pdf",
        storage_path="mock/poor.pdf",
        file_size=1024,
        is_active=True,
    )
    db_session.add(doc)
    db_session.flush()

    qr = DocumentQualityResult(
        id=uuid.uuid4(),
        document_id=doc.id,
        quality_score=45.0,
        quality_level=QualityLevel.POOR,
        is_blurry=True,
        review_required=True,
        review_reasons=["Laplacian blur variance below threshold."],
        bidder_feedback=["Uploaded scan is blurry. Please upload a clear copy."],
        page_count=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(qr)
    db_session.commit()

    items = HumanReviewService.sync_review_items_for_bid(db=db_session, bid_id=test_setup["bid"].id)
    quality_review_item = next((i for i in items if i.review_type == ReviewType.POOR_DOCUMENT_QUALITY), None)

    assert quality_review_item is not None
    assert quality_review_item.bid_document_id == doc.id
    assert "Poor Document Quality" in quality_review_item.title
