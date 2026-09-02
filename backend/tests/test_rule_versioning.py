"""
Unit and Integration Tests for Part 15: Compliance Rule Version History
Verifies version creation, sequential numbering, diff calculation,
provenance tracking, reproducible evaluations, lifecycle safeguards, and re-evaluation.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Generator
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.ai_recommendation import AIRecommendationRecord
from app.db.models.audit_event import AuditEvent
from app.db.models.bid import Bid
from app.db.models.bid_decision import BidDecision
from app.db.models.compliance_result import ComplianceResult
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.role import Role
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.tender_requirement_version import TenderRequirementVersion
from app.db.models.user import User
from app.db.session import get_session_factory
from app.schemas.rule_version import TenderRequirementUpdateWithVersionRequest
from app.services.rule_version_service import RuleVersionService
from app.services.tender_requirement_service import create_requirement, update_requirement


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provides an isolated database session for integration tests and rolls back afterward."""
    SessionFactory = get_session_factory()
    session = SessionFactory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def mock_procurement_env(db_session: Session):
    """Sets up a complete procurement test environment with organization, user, profile, and tender."""
    suffix = uuid.uuid4().hex[:6]
    org = Organization(
        id=uuid.uuid4(),
        name=f"Ministry of Energy & Power {suffix}",
        pan_number=f"PAN{suffix.upper()}12",
        organization_type="PROCURING_ENTITY",
        is_active=True,
    )
    db_session.add(org)

    role_proc = db_session.query(Role).filter_by(name="PROCUREMENT_OFFICER").first()
    if not role_proc:
        role_proc = Role(id=uuid.uuid4(), name="PROCUREMENT_OFFICER", description="Procurement Officer Role")
        db_session.add(role_proc)

    profile = Profile(
        id=uuid.uuid4(),
        organization_id=org.id,
        role_id=role_proc.id,
        full_name="Adithya Officer",
        email=f"officer_{suffix}@energy.gov.in",
        phone="+919876543210",
        is_active=True,
    )
    db_session.add(profile)

    user = User(
        id=uuid.uuid4(),
        email=f"officer_{suffix}@energy.gov.in",
        password_hash="hashed_test_password",
        profile_id=profile.id,
        is_active=True,
    )
    db_session.add(user)

    tender = Tender(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by_profile_id=profile.id,
        tender_number=f"TEN-2026-ENG-{suffix.upper()}",
        title="Solar Power Plant Installation 50MW",
        status="DRAFT",
        is_active=True,
    )
    db_session.add(tender)
    db_session.flush()

    return {
        "org": org,
        "role": role_proc,
        "profile": profile,
        "user": user,
        "tender": tender,
    }


def test_initial_version_creation(db_session: Session, mock_procurement_env: dict):
    """Verifies that creating a tender requirement automatically seeds Version 1."""
    env = mock_procurement_env
    user = env["user"]
    tender = env["tender"]

    req = TenderRequirement(
        id=uuid.uuid4(),
        tender_id=tender.id,
        code="FIN-001",
        name="Minimum Annual Turnover",
        description="Bidder must have average turnover >= 50 Cr",
        category="FINANCIAL",
        requirement_type="NUMBER",
        operator="GREATER_THAN_OR_EQUAL",
        expected_value={"value": 50, "unit": "Crore"},
        unit="Crore",
        is_mandatory=True,
        is_critical=True,
        weight=Decimal("20.0"),
        display_order=1,
        is_active=True,
    )
    db_session.add(req)
    db_session.flush()

    v1 = RuleVersionService.create_initial_version(
        db=db_session,
        requirement=req,
        current_user=user,
        change_reason="Initial rule definition",
    )
    db_session.flush()

    assert v1 is not None
    assert v1.version_number == 1
    assert v1.code == "FIN-001"
    assert v1.name == "Minimum Annual Turnover"
    assert v1.operator == "GREATER_THAN_OR_EQUAL"
    assert v1.is_mandatory is True
    assert v1.is_critical is True
    assert req.current_version_number == 1
    assert v1.changed_by_profile_id == user.profile_id


def test_subsequent_version_creation_on_edit(db_session: Session, mock_procurement_env: dict):
    """Verifies that updating requirement parameters increments version and preserves previous version."""
    env = mock_procurement_env
    user = env["user"]
    tender = env["tender"]

    req = TenderRequirement(
        id=uuid.uuid4(),
        tender_id=tender.id,
        code="EXP-001",
        name="Similar Work Experience",
        description="Minimum 3 years experience",
        category="EXPERIENCE",
        requirement_type="NUMBER",
        operator="GREATER_THAN_OR_EQUAL",
        expected_value={"years": 3},
        is_mandatory=True,
        is_critical=False,
        weight=Decimal("15.0"),
        display_order=2,
        is_active=True,
    )
    db_session.add(req)
    db_session.flush()
    RuleVersionService.create_initial_version(db=db_session, requirement=req, current_user=user)
    db_session.flush()

    # Perform update (increase experience threshold to 5 years and make critical)
    update_dto = TenderRequirementUpdateWithVersionRequest(
        expected_value={"years": 5},
        is_critical=True,
        weight=Decimal("25.0"),
        change_reason="Corrigendum #1: Elevated technical requirement threshold",
        corrigendum_number="CORR-01",
    )

    updated_req, new_ver, changed = RuleVersionService.update_requirement_with_version(
        db=db_session,
        tender_id=tender.id,
        requirement_id=req.id,
        data=update_dto,
        current_user=user,
    )

    assert changed is True
    assert updated_req.current_version_number == 2
    assert new_ver.version_number == 2
    assert new_ver.expected_value == {"years": 5}
    assert new_ver.is_critical is True
    assert new_ver.weight == Decimal("25.0")
    assert new_ver.corrigendum_number == "CORR-01"

    # Verify both v1 and v2 exist in history
    versions = RuleVersionService.list_requirement_versions(
        db=db_session,
        tender_id=tender.id,
        requirement_id=req.id,
        current_user=user,
    )
    assert versions.total_versions == 2
    assert versions.versions[0].version_number == 2  # Newest first
    assert versions.versions[1].version_number == 1  # Baseline


def test_deterministic_sequential_version_numbering(db_session: Session, mock_procurement_env: dict):
    """Verifies sequential version numbers 1, 2, 3, 4 upon successive updates."""
    env = mock_procurement_env
    user = env["user"]
    tender = env["tender"]

    req = TenderRequirement(
        id=uuid.uuid4(),
        tender_id=tender.id,
        code="STAT-001",
        name="GST Registration",
        category="STATUTORY",
        requirement_type="BOOLEAN",
        operator="EQUALS",
        expected_value={"required": True},
        is_mandatory=True,
        is_active=True,
    )
    db_session.add(req)
    db_session.flush()
    RuleVersionService.create_initial_version(db=db_session, requirement=req, current_user=user)
    db_session.flush()

    for expected_v in [2, 3, 4]:
        update_dto = TenderRequirementUpdateWithVersionRequest(
            name=f"GST Registration Active (Rev {expected_v})",
            change_reason=f"Revision {expected_v}",
        )
        _, ver, changed = RuleVersionService.update_requirement_with_version(
            db=db_session,
            tender_id=tender.id,
            requirement_id=req.id,
            data=update_dto,
            current_user=user,
        )
        assert changed is True
        assert ver.version_number == expected_v


def test_meaningful_difference_detection_no_op(db_session: Session, mock_procurement_env: dict):
    """Verifies that submitting identical criteria does NOT create a redundant version."""
    env = mock_procurement_env
    user = env["user"]
    tender = env["tender"]

    req = TenderRequirement(
        id=uuid.uuid4(),
        tender_id=tender.id,
        code="TECH-001",
        name="ISO 9001 Certification",
        category="TECHNICAL",
        requirement_type="BOOLEAN",
        operator="EQUALS",
        expected_value={"certified": True},
        is_mandatory=True,
        is_active=True,
    )
    db_session.add(req)
    db_session.flush()
    RuleVersionService.create_initial_version(db=db_session, requirement=req, current_user=user)
    db_session.flush()

    # Submit identical update
    update_dto = TenderRequirementUpdateWithVersionRequest(
        name="ISO 9001 Certification",
        expected_value={"certified": True},
        operator="EQUALS",
    )
    _, ver, changed = RuleVersionService.update_requirement_with_version(
        db=db_session,
        tender_id=tender.id,
        requirement_id=req.id,
        data=update_dto,
        current_user=user,
    )

    assert changed is False
    assert ver.version_number == 1
    assert req.current_version_number == 1


def test_version_comparison_diff(db_session: Session, mock_procurement_env: dict):
    """Verifies that compare_versions outputs accurate field-level diffs with impact highlighting."""
    env = mock_procurement_env
    user = env["user"]
    tender = env["tender"]

    req = TenderRequirement(
        id=uuid.uuid4(),
        tender_id=tender.id,
        code="FIN-002",
        name="Net Worth Requirement",
        category="FINANCIAL",
        requirement_type="NUMBER",
        operator="GREATER_THAN_OR_EQUAL",
        expected_value=10000000,
        is_mandatory=False,
        is_critical=False,
        weight=Decimal("10.0"),
        is_active=True,
    )
    db_session.add(req)
    db_session.flush()
    RuleVersionService.create_initial_version(db=db_session, requirement=req, current_user=user)
    db_session.flush()

    # Update to v2: Make mandatory, critical, and higher expected_value
    update_dto = TenderRequirementUpdateWithVersionRequest(
        expected_value=25000000,
        is_mandatory=True,
        is_critical=True,
        weight=Decimal("20.0"),
        change_reason="Corrigendum #2: Tightened financial viability requirements",
    )
    RuleVersionService.update_requirement_with_version(
        db=db_session,
        tender_id=tender.id,
        requirement_id=req.id,
        data=update_dto,
        current_user=user,
    )

    compare_res = RuleVersionService.compare_versions(
        db=db_session,
        tender_id=tender.id,
        requirement_id=req.id,
        v1_num=1,
        v2_num=2,
        current_user=user,
    )

    assert compare_res.has_differences is True
    assert compare_res.v1_number == 1
    assert compare_res.v2_number == 2
    assert compare_res.differences_count >= 4

    diff_map = {d.field_name: d for d in compare_res.diffs}
    assert diff_map["is_mandatory"].is_different is True
    assert diff_map["is_mandatory"].old_value is False
    assert diff_map["is_mandatory"].new_value is True

    assert diff_map["is_critical"].is_different is True
    assert diff_map["is_critical"].new_value is True

    assert diff_map["expected_value"].is_different is True


def test_rule_update_post_bid_submission_staleness(db_session: Session, mock_procurement_env: dict):
    """
    Verifies tender lifecycle safeguard:
    When a rule is updated on an open tender with submitted bids,
    active score, risk, and AI records are marked STALE while compliance history is preserved.
    """
    env = mock_procurement_env
    user = env["user"]
    tender = env["tender"]

    tender.status = "OPEN"

    req = TenderRequirement(
        id=uuid.uuid4(),
        tender_id=tender.id,
        code="SOL-001",
        name="Module Efficiency",
        category="TECHNICAL",
        requirement_type="NUMBER",
        operator="GREATER_THAN_OR_EQUAL",
        expected_value=20.0,
        is_mandatory=True,
        is_active=True,
    )
    db_session.add(req)
    db_session.flush()
    v1 = RuleVersionService.create_initial_version(db=db_session, requirement=req, current_user=user)

    # Create bidder organization and submitted bid
    bidder_org = Organization(
        id=uuid.uuid4(),
        name=f"SolarTech Solutions {uuid.uuid4().hex[:6]}",
        pan_number=f"PAN{uuid.uuid4().hex[:7].upper()}",
        organization_type="BIDDER",
        is_active=True,
    )
    db_session.add(bidder_org)

    bid = Bid(
        id=uuid.uuid4(),
        tender_id=tender.id,
        bidder_organization_id=bidder_org.id,
        created_by_profile_id=env["profile"].id,
        bid_number=f"BID-SOL-{uuid.uuid4().hex[:6]}",
        status="SUBMITTED",
        is_active=True,
    )
    db_session.add(bid)

    # Initial Compliance Result linked to rule Version 1
    comp_res = ComplianceResult(
        id=uuid.uuid4(),
        bid_id=bid.id,
        tender_id=tender.id,
        tender_requirement_id=req.id,
        rule_version_id=v1.id,
        rule_version_number=1,
        compliance_status="PASS",
        is_current=True,
    )
    db_session.add(comp_res)

    # AI Recommendation & Human Decision
    ai_rec = AIRecommendationRecord(
        id=uuid.uuid4(),
        bid_id=bid.id,
        recommendation="PROCEED",
        recommendation_reason="Compliant with all technical requirements.",
        summary="Automated recommendation summary",
        is_stale=False,
    )
    db_session.add(ai_rec)

    decision = BidDecision(
        id=uuid.uuid4(),
        organization_id=tender.organization_id,
        bid_id=bid.id,
        tender_id=tender.id,
        decision="QUALIFIED",
        reason="Technical criteria passed initial inspection.",
        decision_version=1,
        is_current=True,
        is_stale=False,
        decided_by_profile_id=user.profile_id,
    )
    db_session.add(decision)
    db_session.flush()

    # Update requirement in OPEN tender with change reason
    update_dto = TenderRequirementUpdateWithVersionRequest(
        expected_value=22.0,
        change_reason="Upgraded solar panel efficiency benchmark due to MNRE revised guidelines",
    )
    RuleVersionService.update_requirement_with_version(
        db=db_session,
        tender_id=tender.id,
        requirement_id=req.id,
        data=update_dto,
        current_user=user,
    )

    db_session.refresh(ai_rec)
    db_session.refresh(decision)
    db_session.refresh(comp_res)

    # Evaluations must be marked STALE
    assert ai_rec.is_stale is True
    assert decision.is_stale is True
    assert "Compliance rules updated" in (decision.stale_reason or "")
    # Human verdict is untouched
    assert decision.decision == "QUALIFIED"

    # Historical compliance result remains intact and tied to v1
    assert comp_res.rule_version_number == 1
    assert comp_res.compliance_status == "PASS"


def test_human_decision_protection_on_rule_change(db_session: Session, mock_procurement_env: dict):
    """
    Verifies that updating a rule NEVER alters or overwrites existing human decisions (e.g. QUALIFIED).
    """
    env = mock_procurement_env
    user = env["user"]
    tender = env["tender"]
    profile = env["profile"]
    org = env["org"]

    tender.status = "UNDER_EVALUATION"

    req = TenderRequirement(
        id=uuid.uuid4(),
        tender_id=tender.id,
        code=f"QUAL-{uuid.uuid4().hex[:4].upper()}",
        name="Safety Standard Certification",
        category="TECHNICAL",
        operator="EQUALS",
        expected_value={"standard": "IS-14286"},
        is_mandatory=True,
        is_active=True,
    )
    db_session.add(req)
    db_session.flush()
    RuleVersionService.create_initial_version(db=db_session, requirement=req, current_user=user)

    # Bidder Org
    bidder_org = Organization(
        id=uuid.uuid4(),
        name=f"QualTech Systems {uuid.uuid4().hex[:6]}",
        pan_number=f"PAN{uuid.uuid4().hex[:7].upper()}",
        organization_type="BIDDER",
        is_active=True,
    )
    db_session.add(bidder_org)

    bid = Bid(
        id=uuid.uuid4(),
        tender_id=tender.id,
        bidder_organization_id=bidder_org.id,
        created_by_profile_id=profile.id,
        bid_number=f"BID-DEC-{uuid.uuid4().hex[:6]}",
        status="UNDER_EVALUATION",
        is_active=True,
    )
    db_session.add(bid)

    # Pre-existing human decision
    decision = BidDecision(
        id=uuid.uuid4(),
        organization_id=org.id,
        bid_id=bid.id,
        tender_id=tender.id,
        decision="QUALIFIED",
        reason="Technical and statutory criteria verified satisfactorily.",
        decision_version=1,
        is_current=True,
        is_stale=False,
        decided_by_profile_id=profile.id,
    )
    db_session.add(decision)
    db_session.flush()

    # Rule is updated
    update_dto = TenderRequirementUpdateWithVersionRequest(
        expected_value={"standard": "IS-14286-REV2"},
        change_reason="Corrigendum: Standard updated to revision 2",
    )
    RuleVersionService.update_requirement_with_version(
        db=db_session,
        tender_id=tender.id,
        requirement_id=req.id,
        data=update_dto,
        current_user=user,
    )

    db_session.refresh(decision)

    # Human decision must remain QUALIFIED and intact
    assert decision.decision == "QUALIFIED"
    assert decision.is_current is True
    assert decision.decided_by_profile_id == profile.id


def test_tender_rule_snapshot_replay(db_session: Session, mock_procurement_env: dict):
    """Verifies that get_tender_rule_snapshot retrieves the exact rule version mapping."""
    env = mock_procurement_env
    user = env["user"]
    tender = env["tender"]

    req1 = TenderRequirement(
        id=uuid.uuid4(),
        tender_id=tender.id,
        code="RULE-A",
        name="Rule A",
        operator="EQUALS",
        is_mandatory=True,
        is_active=True,
    )
    req2 = TenderRequirement(
        id=uuid.uuid4(),
        tender_id=tender.id,
        code="RULE-B",
        name="Rule B",
        operator="EQUALS",
        is_mandatory=False,
        is_active=True,
    )
    db_session.add_all([req1, req2])
    db_session.flush()

    RuleVersionService.create_initial_version(db=db_session, requirement=req1, current_user=user)
    RuleVersionService.create_initial_version(db=db_session, requirement=req2, current_user=user)
    db_session.flush()

    # Bump Rule A to version 2
    RuleVersionService.update_requirement_with_version(
        db=db_session,
        tender_id=tender.id,
        requirement_id=req1.id,
        data=TenderRequirementUpdateWithVersionRequest(name="Rule A Revised", change_reason="Rev 2"),
        current_user=user,
    )

    snapshot = RuleVersionService.get_tender_rule_snapshot(db=db_session, tender_id=tender.id)

    assert len(snapshot) == 2
    assert snapshot[req1.id].version_number == 2
    assert snapshot[req2.id].version_number == 1
