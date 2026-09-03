"""
Automated Test Suite for Organization Identity Verification & Duplicate Entity Detection
BidVerify AI — Integrated Bid Compliance Verification Platform for GeM Procurement
"""

import logging
import sys
import uuid
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

from app.db.session import get_engine, get_session_factory
from app.db.base import Base
import app.db.models  # load all models
from app.db.models.organization import Organization
from app.db.models.organization_identity import (
    IdentityMatchStatus,
    OrganizationDuplicateMatch,
    OrganizationDuplicateMatchStatus,
    OrganizationDuplicateMatchType,
    OrganizationIdentityAssessment,
    OrganizationIdentityStatus,
)
from app.services.organization_identity_service import organization_identity_service
from app.verification.normalizers import (
    compare_addresses,
    compare_names,
    extract_pan_from_gstin,
    normalize_org_name,
)


def run_tests():
    logger.info("=" * 60)
    logger.info("STARTING ORGANIZATION IDENTITY & DUPLICATE DETECTION TESTS")
    logger.info("=" * 60)

    # 1. Create all missing tables in database
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    SessionFactory = get_session_factory()
    db = SessionFactory()

    try:
        # Test 1: Name Normalization & Suffix Invariance
        logger.info("\n--- TEST 1: Legal Name Normalization ---")
        n1 = normalize_org_name("ABC Technologies Pvt. Ltd.")
        n2 = normalize_org_name("ABC TECHNOLOGIES PRIVATE LIMITED")
        n3 = normalize_org_name("ABC Technologies Pvt Ltd")
        assert n1 == n2 == n3 == "ABC TECHNOLOGIES PRIVATE LIMITED", f"Mismatch: {n1}, {n2}, {n3}"
        stat, conf = compare_names("ABC Technologies Pvt. Ltd.", "ABC TECHNOLOGIES PRIVATE LIMITED")
        assert stat == "MATCH" and conf == 1.0, f"Failed compare_names: {stat}, {conf}"
        logger.info("✓ Legal name normalization verified: '%s'", n1)

        # Test 2: PAN from GSTIN Embedded Extraction
        logger.info("\n--- TEST 2: Embedded PAN in GSTIN Validation ---")
        valid_gstin = "33ABCDE1234F1Z5"
        extracted_pan = extract_pan_from_gstin(valid_gstin)
        assert extracted_pan == "ABCDE1234F", f"Expected ABCDE1234F, got {extracted_pan}"
        logger.info("✓ Extracted embedded PAN: %s from GSTIN: %s", extracted_pan, valid_gstin)

        # Test 3: Address Comparison
        logger.info("\n--- TEST 3: Address Comparison ---")
        addr_a = "Plot 42, Electronics City Phase 1, Bangalore, Karnataka - 560100"
        addr_b = "No. 42 Electronics City, Phase-I, Bengaluru 560100"
        addr_c = "100 Anna Salai, Guindy, Chennai, Tamil Nadu - 600032"

        stat_match, _ = compare_addresses(addr_a, addr_b)
        stat_mismatch, _ = compare_addresses(addr_a, addr_c)
        assert stat_match in ("MATCH", "PARTIAL_MATCH"), f"Expected match/partial, got {stat_match}"
        assert stat_mismatch == "MISMATCH", f"Expected mismatch for different PIN/state, got {stat_mismatch}"
        logger.info("✓ Address token & PIN code comparison verified (Match: %s, Mismatch: %s)", stat_match, stat_mismatch)

        # Test 4: Single Org Coherent Identity Assessment
        logger.info("\n--- TEST 4: Single Org Coherent Identity Assessment ---")
        import random
        rand_num = f"{random.randint(1000, 9999)}"
        test_uid = uuid.uuid4().hex[:4].upper()
        pan_1 = f"ABCDE{rand_num}F"
        gstin_1 = f"33{pan_1}1Z5"

        org_1 = Organization(
            name=f"Apex Cloud Systems Pvt Ltd {test_uid}",
            trade_name="Apex Cloud",
            pan_number=pan_1,
            gstin=gstin_1,
            udyam_number=f"UDYAM-TN-01-{rand_num}",
            cin_llpin=f"U72900TN2020PTC{rand_num}0",
            registered_address="Tidel Park, Tharamani, Chennai 600113",
            city="Chennai",
            state="Tamil Nadu",
            pincode="600113",
            country="India",
        )
        db.add(org_1)
        db.commit()
        db.refresh(org_1)

        assessment_1 = organization_identity_service.evaluate_organization_identity(
            db=db,
            organization_id=org_1.id,
            actor_name="Automated Test",
        )

        assert assessment_1.identity_score >= 80.0, f"Expected high score, got {assessment_1.identity_score}"
        assert assessment_1.pan_gst_embedded_status == IdentityMatchStatus.MATCH, f"Expected MATCH, got {assessment_1.pan_gst_embedded_status}"
        assert assessment_1.identity_status in (OrganizationIdentityStatus.CONSISTENT, OrganizationIdentityStatus.VERIFIED), f"Got {assessment_1.identity_status}"
        logger.info("✓ Org 1 Assessment: Score=%.1f, Status=%s, Embedded PAN Status=%s", assessment_1.identity_score, assessment_1.identity_status, assessment_1.pan_gst_embedded_status)

        # Test 5: Case C: Embedded PAN / GSTIN Mismatch
        logger.info("\n--- TEST 5: Case C - Standalone PAN vs GSTIN Embedded PAN Mismatch ---")
        conflicting_gstin = f"33XYZWV9999P1Z5"  # embedded PAN is XYZWV9999P, conflicting with pan_1
        org_conflict = Organization(
            name=f"Conflict Enterprise Pvt Ltd {test_uid}",
            pan_number=pan_1,
            gstin=conflicting_gstin,
            registered_address="Industrial Area, Gurgaon 122001",
        )
        db.add(org_conflict)
        db.commit()
        db.refresh(org_conflict)

        assessment_conflict = organization_identity_service.evaluate_organization_identity(
            db=db,
            organization_id=org_conflict.id,
            actor_name="Automated Test",
        )

        assert assessment_conflict.pan_gst_embedded_status == IdentityMatchStatus.MISMATCH, f"Expected MISMATCH, got {assessment_conflict.pan_gst_embedded_status}"
        assert assessment_conflict.identity_status in (OrganizationIdentityStatus.MISMATCH, OrganizationIdentityStatus.REVIEW_REQUIRED), f"Expected MISMATCH, got {assessment_conflict.identity_status}"
        logger.info("✓ Conflict Org correctly flagged: Status=%s, Embedded PAN Status=%s", assessment_conflict.identity_status, assessment_conflict.pan_gst_embedded_status)

        # Test 6: Case A: Reused Strong Identifiers (Potential Duplicate Entity)
        logger.info("\n--- TEST 6: Case A - Potential Duplicate Organization Detection ---")
        org_dup = Organization(
            name=f"Apex Cloud Systems Private Limited {test_uid}",  # slightly different name format
            trade_name="Apex Solutions",
            pan_number=pan_1,  # Same PAN as Org 1
            gstin=gstin_1,  # Same GSTIN as Org 1
            registered_address="Tidel Park, Chennai 600113",
        )
        db.add(org_dup)
        db.commit()
        db.refresh(org_dup)

        dup_matches = organization_identity_service.detect_organization_duplicates(
            db=db,
            organization_id=org_dup.id,
        )

        assert len(dup_matches) > 0, "Expected duplicate matches to be detected!"
        match_found = next((m for m in dup_matches if m.match_type in (OrganizationDuplicateMatchType.SAME_LEGAL_ENTITY, OrganizationDuplicateMatchType.SAME_PAN)), None)
        assert match_found is not None, f"Expected SAME_LEGAL_ENTITY or SAME_PAN match, found types: {[m.match_type for m in dup_matches]}"
        assert match_found.status == OrganizationDuplicateMatchStatus.DETECTED
        logger.info("✓ Duplicate Entity Detected: Match Type=%s, Similarity=%.1f, Matched IDs=%s", match_found.match_type, match_found.similarity_score, match_found.matched_identifiers)

        # Test 7: Case B: Same Name with Different Legal Identity
        logger.info("\n--- TEST 7: Case B - Same Name Different Legal Identity Disambiguation ---")
        rand_diff = f"{random.randint(1000, 9999)}"
        pan_diff = f"DIFFE{rand_diff}P"
        gstin_diff = f"27{pan_diff}1Z2"

        org_diff_identity = Organization(
            name=f"Apex Cloud Systems Pvt Ltd {test_uid}",  # Same name as Org 1
            pan_number=pan_diff,  # Different PAN
            gstin=gstin_diff,  # Different GSTIN
            registered_address="Nariman Point, Mumbai 400021",
        )
        db.add(org_diff_identity)
        db.commit()
        db.refresh(org_diff_identity)

        diff_matches = organization_identity_service.detect_organization_duplicates(
            db=db,
            organization_id=org_diff_identity.id,
        )

        diff_name_match = next((m for m in diff_matches if m.organization_a_id == min(org_1.id, org_diff_identity.id) and m.organization_b_id == max(org_1.id, org_diff_identity.id)), None)
        assert diff_name_match is not None, "Expected match record between org_1 and org_diff_identity"
        assert diff_name_match.match_type in (OrganizationDuplicateMatchType.SAME_NAME_DIFFERENT_IDENTITY, OrganizationDuplicateMatchType.HIGH_NAME_SIMILARITY), f"Expected SAME_NAME_DIFFERENT_IDENTITY, got {diff_name_match.match_type}"
        logger.info("✓ Disambiguation Verified: Match Type='%s' (Explicitly identified as distinct legal entities with similar name)", diff_name_match.match_type)

        # Test 8: Human Resolution of Duplicate Match
        logger.info("\n--- TEST 8: Human Review Resolution ---")
        from app.db.models.user import User
        user = db.query(User).first()
        user_id = user.id if user else None
        if not user_id:
            test_user = User(email=f"officer_{test_uid}@test.local", password_hash="dummy")
            db.add(test_user)
            db.commit()
            user_id = test_user.id

        resolved = organization_identity_service.resolve_duplicate_match(
            db=db,
            match_id=diff_name_match.id,
            user_id=user_id,
            new_status=OrganizationDuplicateMatchStatus.CONFIRMED_DISTINCT,
            notes="Verified through MCA registry: Separate legal corporations registered in different states.",
        )
        assert resolved.status == OrganizationDuplicateMatchStatus.CONFIRMED_DISTINCT
        logger.info("✓ Human Resolution Recorded: Status=%s", resolved.status)

        logger.info("\n" + "=" * 60)
        logger.info("ALL ORGANIZATION IDENTITY & DUPLICATE TESTS PASSED (8/8)!")
        logger.info("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    run_tests()
