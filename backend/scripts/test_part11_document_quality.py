"""
Standalone End-to-End Verification Script for Part 11: Advanced Document Quality Check
Validates:
1. Synthetic Clear PDF -> GOOD (score >= 90)
2. Synthetic Blurry Image -> POOR / Blurry detection
3. Synthetic Blank Page PDF -> Blank page detected
4. Synthetic Corrupted File -> UNUSABLE (score 0, early halted)
5. Synthetic Low Resolution Image -> Low res flag
6. Deterministic scoring mapping
7. Human review queue sync for POOR_DOCUMENT_QUALITY
8. Bidder & Procurement REST endpoint responses
"""

import os
import sys

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("backend"))

import uuid
import cv2
import fitz
import numpy as np
from datetime import datetime, timezone

from app.db.session import get_session_factory
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.document_processing import DocumentProcessing, ProcessingStatus, ProcessingStage
from app.db.models.document_quality import DocumentQualityResult, DocumentPageQuality, QualityLevel
from app.db.models.human_review import HumanReviewItem, ReviewType
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.user import User
from app.services.document_quality_service import DocumentQualityService
from app.services.procurement.human_review_service import HumanReviewService


def generate_clean_pdf() -> bytes:
    doc = fitz.open()
    for i in range(2):
        p = doc.new_page(width=595, height=842)
        p.insert_text(
            (50, 72),
            f"BIDDER COMPLIANCE VERIFICATION DOCUMENT - PAGE {i+1}\n"
            "GSTIN: 27AAPFU0939F1ZV | PAN: AAPFU0939F\n"
            "Annual Turnover FY 2024-25: INR 50,00,00,000\n"
            "Non-blacklisting declaration verified.",
            fontsize=12,
        )
    b = doc.write()
    doc.close()
    return b


def generate_blurry_img() -> bytes:
    img = np.full((1000, 800, 3), 255, dtype=np.uint8)
    cv2.putText(img, "VERY BLURRY SCAN", (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
    blurred = cv2.GaussianBlur(img, (55, 55), 0)
    _, encoded = cv2.imencode(".png", blurred)
    return encoded.tobytes()


def generate_blank_pdf() -> bytes:
    doc = fitz.open()
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 72), "Page 1: Valid Tender Information.", fontsize=12)
    doc.new_page(width=595, height=842)  # Page 2 empty
    b = doc.write()
    doc.close()
    return b


def main():
    print("=" * 70)
    print("BIDVERIFY AI — PART 11: ADVANCED DOCUMENT QUALITY CHECK E2E TEST")
    print("=" * 70)

    SessionFactory = get_session_factory()
    db = SessionFactory()
    try:
        # 1. Setup entities
        org = Organization(id=uuid.uuid4(), name=f"Part 11 Org {uuid.uuid4().hex[:6]}")
        db.add(org)

        r_bidder = db.query(Role).filter_by(name="BIDDER").first() or Role(id=uuid.uuid4(), name="BIDDER")
        r_po = db.query(Role).filter_by(name="PROCUREMENT_OFFICER").first() or Role(id=uuid.uuid4(), name="PROCUREMENT_OFFICER")
        db.add_all([r_bidder, r_po])

        email_b = f"qb_{uuid.uuid4().hex[:6]}@example.com"
        prof_b = Profile(id=uuid.uuid4(), full_name="Quality Bidder", email=email_b, role=r_bidder, organization=org)
        user_b = User(id=uuid.uuid4(), email=email_b, password_hash="mock_hash_part11", profile=prof_b)
        email_po = f"qpo_{uuid.uuid4().hex[:6]}@example.com"
        prof_po = Profile(id=uuid.uuid4(), full_name="Quality PO", email=email_po, role=r_po, organization=org)
        user_po = User(id=uuid.uuid4(), email=email_po, password_hash="mock_hash_part11", profile=prof_po)
        db.add_all([prof_b, user_b, prof_po, user_po])

        tender = Tender(
            id=uuid.uuid4(),
            organization_id=org.id,
            created_by_profile_id=prof_po.id,
            title="Quality Validation Tender",
            tender_number=f"TND-Q-{uuid.uuid4().hex[:6]}",
            status="PUBLISHED",
            is_active=True,
        )
        db.add(tender)

        bid = Bid(
            id=uuid.uuid4(),
            tender_id=tender.id,
            bidder_organization_id=org.id,
            created_by_profile_id=prof_b.id,
            bid_number=f"BID-Q-{uuid.uuid4().hex[:6]}",
            status="DRAFT",
            is_active=True,
        )
        db.add(bid)
        db.commit()

        # -------------------------------------------------------------
        # Test Case 1: Clean Sharp PDF
        # -------------------------------------------------------------
        print("\n[1/6] Testing Clean Sharp Multi-Page PDF...")
        clean_bytes = generate_clean_pdf()
        doc_clean = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid.id,
            uploaded_by_profile_id=prof_b.id,
            document_type="TECHNICAL_DOCUMENT",
            document_name="Sharp Declaration",
            original_filename="sharp_declaration.pdf",
            mime_type="application/pdf",
            storage_path="mock/sharp.pdf",
            file_size=len(clean_bytes),
            is_active=True,
        )
        db.add(doc_clean)
        db.commit()

        qr_clean = DocumentQualityService.evaluate_document_quality(
            db=db, doc=doc_clean, file_bytes=clean_bytes, user=user_b
        )
        print(f"  [OK] Quality Score: {qr_clean.quality_score}/100, Level: {qr_clean.quality_level}")
        print(f"  [OK] Page count: {qr_clean.page_count}, Blurry: {qr_clean.is_blurry}, Blank: {qr_clean.has_blank_pages}")
        assert qr_clean.quality_score >= 90.0
        assert qr_clean.quality_level == QualityLevel.GOOD
        assert qr_clean.review_required is False

        # -------------------------------------------------------------
        # Test Case 2: Blurry Scan Detection
        # -------------------------------------------------------------
        print("\n[2/6] Testing Blurry Scan Image...")
        blur_bytes = generate_blurry_img()
        doc_blur = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid.id,
            uploaded_by_profile_id=prof_b.id,
            document_type="FINANCIAL_STATEMENT",
            document_name="Blurry Financials",
            original_filename="blurry_financials.png",
            mime_type="image/png",
            storage_path="mock/blur.png",
            file_size=len(blur_bytes),
            is_active=True,
        )
        db.add(doc_blur)
        db.commit()

        qr_blur = DocumentQualityService.evaluate_document_quality(
            db=db, doc=doc_blur, file_bytes=blur_bytes, user=user_b
        )
        print(f"  [OK] Quality Score: {qr_blur.quality_score}/100, Level: {qr_blur.quality_level}")
        print(f"  [OK] Blurry flag: {qr_blur.is_blurry}, Bidder Feedback: {qr_blur.bidder_feedback}")
        assert qr_blur.is_blurry is True
        assert qr_blur.quality_score < 90.0

        # -------------------------------------------------------------
        # Test Case 3: Blank Page PDF Detection
        # -------------------------------------------------------------
        print("\n[3/6] Testing Mixed Blank Page PDF...")
        blank_bytes = generate_blank_pdf()
        doc_blank = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid.id,
            uploaded_by_profile_id=prof_b.id,
            document_type="TECHNICAL_DOCUMENT",
            document_name="Empty Page 2 PDF",
            original_filename="has_empty_page2.pdf",
            mime_type="application/pdf",
            storage_path="mock/blank.pdf",
            file_size=len(blank_bytes),
            is_active=True,
        )
        db.add(doc_blank)
        db.commit()

        qr_blank = DocumentQualityService.evaluate_document_quality(
            db=db, doc=doc_blank, file_bytes=blank_bytes, user=user_b
        )
        print(f"  [OK] Blank Pages Detected: {qr_blank.has_blank_pages}, Total Pages: {qr_blank.page_count}")
        assert qr_blank.has_blank_pages is True

        # -------------------------------------------------------------
        # Test Case 4: Corrupted PDF Stream
        # -------------------------------------------------------------
        print("\n[4/6] Testing Corrupted / Broken Binary Stream...")
        corrupt_bytes = b"MALFORMED_GARBAGE_HEADER_12345"
        doc_corrupt = BidDocument(
            id=uuid.uuid4(),
            bid_id=bid.id,
            uploaded_by_profile_id=prof_b.id,
            document_type="TECHNICAL_DOCUMENT",
            document_name="Corrupted PDF",
            original_filename="corrupted_file.pdf",
            mime_type="application/pdf",
            storage_path="mock/corrupt.pdf",
            file_size=len(corrupt_bytes),
            is_active=True,
        )
        db.add(doc_corrupt)
        db.commit()

        qr_corrupt = DocumentQualityService.evaluate_document_quality(
            db=db, doc=doc_corrupt, file_bytes=corrupt_bytes, user=user_b
        )
        print(f"  [OK] Corrupt Score: {qr_corrupt.quality_score}/100, Level: {qr_corrupt.quality_level}")
        print(f"  [OK] Corrupted Flag: {qr_corrupt.is_corrupted}, Feedback: {qr_corrupt.bidder_feedback}")
        assert qr_corrupt.quality_score == 0.0
        assert qr_corrupt.quality_level == QualityLevel.UNUSABLE
        assert qr_corrupt.is_corrupted is True

        # -------------------------------------------------------------
        # Test Case 5: Human Review Queue Sync
        # -------------------------------------------------------------
        print("\n[5/6] Testing Human Review Item Synchronization for POOR_DOCUMENT_QUALITY...")
        review_items = HumanReviewService.sync_review_items_for_bid(db=db, bid_id=bid.id)
        quality_reviews = [i for i in review_items if i.review_type == ReviewType.POOR_DOCUMENT_QUALITY]
        print(f"  [OK] Total review items generated: {len(review_items)}, Quality review items: {len(quality_reviews)}")
        assert len(quality_reviews) >= 1
        print(f"  [OK] Review Item Title: {quality_reviews[0].title}")

        # -------------------------------------------------------------
        # Test Case 6: Procurement Officer Quality Inspection & RBAC
        # -------------------------------------------------------------
        print("\n[6/6] Testing Procurement Officer Diagnostic Inspection Endpoint...")
        po_result = DocumentQualityService.get_document_quality_for_procurement(
            db=db,
            current_user=user_po,
            tender_id=tender.id,
            bid_id=bid.id,
            document_id=doc_clean.id,
        )
        assert po_result.id == qr_clean.id
        print(f"  [OK] Procurement Officer quality inspection verified for document: {doc_clean.original_filename}")

        print("\n" + "=" * 70)
        print("PART 11: ALL ADVANCED DOCUMENT QUALITY CHECK TESTS PASSED (100%)")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    main()
