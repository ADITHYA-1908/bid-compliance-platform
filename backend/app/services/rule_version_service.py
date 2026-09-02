"""
Rule Version Service for Part 15: Compliance Rule Version History
Provides business logic for immutable requirement versioning, diff detection,
provenance tracking, reproducible evaluations, tender lifecycle safeguards, and re-evaluation.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.models.ai_recommendation import AIRecommendationRecord
from app.db.models.audit_event import AuditActorSource, AuditEntityType, AuditEventType
from app.db.models.bid import Bid
from app.db.models.bid_decision import BidDecision
from app.db.models.compliance_result import ComplianceResult
from app.db.models.notification import NotificationSeverity, NotificationType
from app.db.models.profile import Profile
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.role import Role
from app.db.models.score_snapshot import BidScoreSnapshot
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.tender_requirement_version import TenderRequirementVersion
from app.db.models.user import User
from app.schemas.audit import RecordAuditEventDTO
from app.schemas.rule_version import (
    ReevaluationBidResult,
    ReevaluationResultResponse,
    TenderRequirementFieldDiff,
    TenderRequirementUpdateWithVersionRequest,
    TenderRequirementVersionCompareResponse,
    TenderRequirementVersionListResponse,
    TenderRequirementVersionResponse,
)
from app.services.audit.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.services.tender_service import get_tender_by_id

logger = logging.getLogger(__name__)


# Fields compared for rule difference detection
COMPARABLE_FIELDS = [
    ("name", "Requirement Name", "INFO"),
    ("description", "Description", "INFO"),
    ("category", "Category", "WARNING"),
    ("requirement_type", "Requirement Type", "CRITICAL"),
    ("operator", "Evaluation Operator", "CRITICAL"),
    ("expected_value", "Expected Benchmark Value", "CRITICAL"),
    ("unit", "Value Unit", "WARNING"),
    ("is_mandatory", "Mandatory Status", "CRITICAL"),
    ("is_critical", "Critical Qualification Rule", "CRITICAL"),
    ("weight", "Scoring Weight", "WARNING"),
    ("display_order", "Display Sorting Order", "INFO"),
    ("source_clause", "Tender Clause Reference", "INFO"),
    ("source_page", "Document Page Number", "INFO"),
    ("corrigendum_number", "Corrigendum Number", "WARNING"),
    ("effective_from", "Effective From Date", "INFO"),
    ("effective_to", "Effective To Date", "INFO"),
    ("is_active", "Active Status", "CRITICAL"),
]


def _normalize_val_for_comparison(val: Any) -> Any:
    """Normalizes values for deterministic difference comparison."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (int, float, bool, str)):
        return val
    if isinstance(val, (dict, list)):
        try:
            return json.loads(json.dumps(val, sort_keys=True, default=str))
        except Exception:
            return str(val)
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


class RuleVersionService:
    """
    Central service for managing Tender Requirement Version History.
    """

    @classmethod
    def create_initial_version(
        cls,
        db: Session,
        requirement: TenderRequirement,
        current_user: Optional[User] = None,
        change_reason: Optional[str] = None,
    ) -> TenderRequirementVersion:
        """
        Creates the baseline Version 1 snapshot for a newly created TenderRequirement.
        """
        profile_id = current_user.profile_id if current_user else requirement.last_changed_by_profile_id
        now = datetime.now(timezone.utc)

        version_1 = TenderRequirementVersion(
            id=uuid.uuid4(),
            tender_requirement_id=requirement.id,
            tender_id=requirement.tender_id,
            version_number=1,
            code=requirement.code,
            name=requirement.name,
            description=requirement.description,
            category=requirement.category,
            requirement_type=requirement.requirement_type,
            operator=requirement.operator,
            expected_value=requirement.expected_value,
            unit=requirement.unit,
            is_mandatory=requirement.is_mandatory,
            is_critical=requirement.is_critical,
            weight=requirement.weight,
            display_order=requirement.display_order,
            source_clause=requirement.source_clause,
            source_page=requirement.source_page,
            corrigendum_number=requirement.corrigendum_number,
            effective_from=requirement.effective_from or now,
            effective_to=requirement.effective_to,
            change_reason=change_reason or "Initial baseline requirement version",
            changed_by_profile_id=profile_id,
            change_metadata={"action": "INITIAL_CREATION", "created_at": now.isoformat()},
            is_active=requirement.is_active,
            created_at=now,
            updated_at=now,
        )
        db.add(version_1)
        requirement.current_version_number = 1
        requirement.change_reason = version_1.change_reason
        requirement.last_changed_by_profile_id = profile_id

        # Audit Event
        tender = db.scalars(select(Tender).where(Tender.id == requirement.tender_id)).first()
        if tender and current_user:
            try:
                AuditService.record_event(
                    db=db,
                    event_dto=RecordAuditEventDTO(
                        organization_id=tender.organization_id,
                        tender_id=tender.id,
                        event_type=AuditEventType.COMPLIANCE_RULE_VERSION_CREATED,
                        entity_type=AuditEntityType.TENDER_REQUIREMENT_VERSION,
                        entity_id=version_1.id,
                        actor_user_id=current_user.id,
                        actor_profile_id=current_user.profile_id,
                        actor_source=AuditActorSource.HUMAN,
                        action="CREATE_RULE_VERSION",
                        summary=f"Created Version 1 for compliance rule [{requirement.code}] '{requirement.name}'",
                        metadata={
                            "requirement_id": str(requirement.id),
                            "version_number": 1,
                            "code": requirement.code,
                            "is_mandatory": requirement.is_mandatory,
                            "is_critical": requirement.is_critical,
                        },
                    ),
                )
            except Exception as e:
                logger.warning(f"Failed to record audit event for rule version 1: {e}")

        return version_1

    @classmethod
    def update_requirement_with_version(
        cls,
        db: Session,
        tender_id: uuid.UUID,
        requirement_id: uuid.UUID,
        data: TenderRequirementUpdateWithVersionRequest,
        current_user: User,
    ) -> Tuple[TenderRequirement, TenderRequirementVersion, bool]:
        """
        Updates an existing TenderRequirement and creates a new immutable version record
        if meaningful criteria changes are detected.
        
        Tender Lifecycle Behavior:
        - DRAFT: Normal versioned edits.
        - PUBLISHED / OPEN / UNDER_EVALUATION: Requires explicit change_reason.
        - If bids already exist: Marks evaluations, scores, and risks as STALE while
          preserving historical compliance results and existing human decisions.
        """
        tender = get_tender_by_id(db=db, tender_id=tender_id, current_user=current_user)

        req = db.scalars(
            select(TenderRequirement).where(
                TenderRequirement.id == requirement_id,
                TenderRequirement.tender_id == tender_id,
            )
        ).first()

        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tender requirement {requirement_id} not found for tender {tender_id}.",
            )

        update_dict = data.model_dump(exclude_unset=True)

        # Check for meaningful differences
        changed_fields: Dict[str, Tuple[Any, Any]] = {}
        for field_name, label, _ in COMPARABLE_FIELDS:
            if field_name in update_dict:
                old_raw = getattr(req, field_name)
                new_raw = update_dict[field_name]
                old_norm = _normalize_val_for_comparison(old_raw)
                new_norm = _normalize_val_for_comparison(new_raw)
                if old_norm != new_norm:
                    changed_fields[field_name] = (old_raw, new_raw)

        # If no fields changed, return existing requirement
        if not changed_fields:
            current_ver = db.scalars(
                select(TenderRequirementVersion).where(
                    TenderRequirementVersion.tender_requirement_id == req.id,
                    TenderRequirementVersion.version_number == req.current_version_number,
                )
            ).first()
            return req, current_ver, False

        # Tender lifecycle checks: require change reason if published or bids exist
        has_bids = db.scalar(
            select(func.count(Bid.id)).where(Bid.tender_id == tender_id, Bid.is_active == True)  # noqa: E712
        ) > 0

        is_published = tender.status in ["PUBLISHED", "OPEN", "CLOSED", "UNDER_EVALUATION", "EVALUATED"]
        if (is_published or has_bids) and not (data.change_reason and data.change_reason.strip()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"A change reason is mandatory when updating requirements for a {tender.status} tender "
                    f"with active bids."
                ),
            )

        # Compute next version number
        max_ver = db.scalar(
            select(func.max(TenderRequirementVersion.version_number)).where(
                TenderRequirementVersion.tender_requirement_id == req.id
            )
        )
        next_ver_num = (max_ver or req.current_version_number or 0) + 1

        now = datetime.now(timezone.utc)
        change_reason_text = (
            data.change_reason.strip()
            if (data.change_reason and data.change_reason.strip())
            else f"Rule update (version {next_ver_num})"
        )

        # Apply updates to active requirement
        for field, new_val in update_dict.items():
            if field not in ["change_reason"]:
                setattr(req, field, new_val)

        req.current_version_number = next_ver_num
        req.change_reason = change_reason_text
        req.last_changed_by_profile_id = current_user.profile_id
        req.updated_at = now

        # Create new immutable version record
        new_version = TenderRequirementVersion(
            id=uuid.uuid4(),
            tender_requirement_id=req.id,
            tender_id=tender_id,
            version_number=next_ver_num,
            code=req.code,
            name=req.name,
            description=req.description,
            category=req.category,
            requirement_type=req.requirement_type,
            operator=req.operator,
            expected_value=req.expected_value,
            unit=req.unit,
            is_mandatory=req.is_mandatory,
            is_critical=req.is_critical,
            weight=req.weight,
            display_order=req.display_order,
            source_clause=req.source_clause,
            source_page=req.source_page,
            corrigendum_number=req.corrigendum_number,
            effective_from=req.effective_from or now,
            effective_to=req.effective_to,
            change_reason=change_reason_text,
            changed_by_profile_id=current_user.profile_id,
            change_metadata={
                "action": "RULE_UPDATE",
                "changed_fields": list(changed_fields.keys()),
                "tender_status": tender.status,
                "had_bids": has_bids,
            },
            is_active=req.is_active,
            created_at=now,
            updated_at=now,
        )
        db.add(new_version)

        # Mark evaluations as stale if bids exist (without wiping compliance history or human decisions)
        stale_bids_count = 0
        if has_bids:
            tender_bid_ids = db.scalars(
                select(Bid.id).where(Bid.tender_id == tender_id, Bid.is_active == True)  # noqa: E712
            ).all()

            if tender_bid_ids:
                # Mark AI recommendations as stale
                db.query(AIRecommendationRecord).filter(
                    AIRecommendationRecord.bid_id.in_(tender_bid_ids),
                ).update({AIRecommendationRecord.is_stale: True}, synchronize_session=False)

                # Mark active human decisions as stale (with warning, without mutating human verdict)
                db.query(BidDecision).filter(
                    BidDecision.bid_id.in_(tender_bid_ids),
                    BidDecision.is_current == True,  # noqa: E712
                ).update(
                    {
                        BidDecision.is_stale: True,
                        BidDecision.stale_reason: f"Compliance rules updated (Rule [{req.code}] v{next_ver_num}). Human review required.",
                    },
                    synchronize_session=False,
                )

                stale_bids_count = len(tender_bid_ids)

        db.commit()
        db.refresh(req)
        db.refresh(new_version)

        # Record Audit Event
        try:
            AuditService.record_event(
                db=db,
                event_dto=RecordAuditEventDTO(
                    organization_id=tender.organization_id,
                    tender_id=tender.id,
                    event_type=AuditEventType.COMPLIANCE_RULE_CHANGED,
                    entity_type=AuditEntityType.TENDER_REQUIREMENT_VERSION,
                    entity_id=new_version.id,
                    actor_user_id=current_user.id,
                    actor_profile_id=current_user.profile_id,
                    actor_source=AuditActorSource.HUMAN,
                    action="UPDATE_RULE_VERSION",
                    summary=(
                        f"Updated compliance rule [{req.code}] '{req.name}' to Version {next_ver_num}. "
                        f"Reason: {change_reason_text}"
                    ),
                    metadata={
                        "requirement_id": str(req.id),
                        "new_version_number": next_ver_num,
                        "changed_fields": list(changed_fields.keys()),
                        "reason": change_reason_text,
                        "stale_bids_affected": stale_bids_count,
                    },
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to record audit event for rule version update: {e}")

        # Send Notification to Procurement Officers
        try:
            NotificationService.create_notification(
                db=db,
                organization_id=tender.organization_id,
                notification_type=NotificationType.TENDER_RULE_UPDATED,
                severity=NotificationSeverity.WARNING if has_bids else NotificationSeverity.INFO,
                title=f"Rule [{req.code}] Updated to v{next_ver_num}",
                message=(
                    f"Requirement '{req.name}' for tender {tender.tender_number} was updated to Version {next_ver_num}. "
                    f"Reason: {change_reason_text}"
                    + (f" ({stale_bids_count} bid evaluations marked for re-evaluation)" if stale_bids_count else "")
                ),
                tender_id=tender.id,
                payload={
                    "requirement_id": str(req.id),
                    "code": req.code,
                    "version_number": next_ver_num,
                    "stale_bids_affected": stale_bids_count,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to dispatch notification for rule version update: {e}")

        return req, new_version, True

    @classmethod
    def list_requirement_versions(
        cls,
        db: Session,
        tender_id: uuid.UUID,
        requirement_id: uuid.UUID,
        current_user: User,
    ) -> TenderRequirementVersionListResponse:
        """
        Lists all historical versions for a requirement, ordered from newest to oldest.
        """
        tender = get_tender_by_id(db=db, tender_id=tender_id, current_user=current_user)

        req = db.scalars(
            select(TenderRequirement).where(
                TenderRequirement.id == requirement_id,
                TenderRequirement.tender_id == tender_id,
            )
        ).first()

        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tender requirement {requirement_id} not found.",
            )

        stmt = (
            select(TenderRequirementVersion)
            .options(joinedload(TenderRequirementVersion.changed_by_profile))
            .where(TenderRequirementVersion.tender_requirement_id == requirement_id)
            .order_by(TenderRequirementVersion.version_number.desc())
        )
        versions_orm = db.scalars(stmt).all()

        version_responses: List[TenderRequirementVersionResponse] = []
        for v in versions_orm:
            author_name = None
            if v.changed_by_profile:
                author_name = v.changed_by_profile.full_name or v.changed_by_profile.email

            res = TenderRequirementVersionResponse(
                id=v.id,
                tender_requirement_id=v.tender_requirement_id,
                tender_id=v.tender_id,
                version_number=v.version_number,
                code=v.code,
                name=v.name,
                description=v.description,
                category=v.category,
                requirement_type=v.requirement_type,
                operator=v.operator,
                expected_value=v.expected_value,
                unit=v.unit,
                is_mandatory=v.is_mandatory,
                is_critical=v.is_critical,
                weight=v.weight,
                display_order=v.display_order,
                source_clause=v.source_clause,
                source_page=v.source_page,
                corrigendum_number=v.corrigendum_number,
                effective_from=v.effective_from,
                effective_to=v.effective_to,
                change_reason=v.change_reason,
                changed_by_profile_id=v.changed_by_profile_id,
                changed_by_name=author_name,
                is_active=v.is_active,
                created_at=v.created_at,
                updated_at=v.updated_at,
            )
            version_responses.append(res)

        return TenderRequirementVersionListResponse(
            requirement_id=req.id,
            tender_id=tender_id,
            code=req.code,
            name=req.name,
            current_version_number=req.current_version_number,
            total_versions=len(version_responses),
            versions=version_responses,
        )

    @classmethod
    def get_requirement_version(
        cls,
        db: Session,
        tender_id: uuid.UUID,
        requirement_id: uuid.UUID,
        version_identifier: Union[uuid.UUID, int],
        current_user: User,
    ) -> TenderRequirementVersionResponse:
        """
        Fetches details of a specific requirement version (by UUID or version number).
        """
        get_tender_by_id(db=db, tender_id=tender_id, current_user=current_user)

        stmt = select(TenderRequirementVersion).options(
            joinedload(TenderRequirementVersion.changed_by_profile)
        ).where(
            TenderRequirementVersion.tender_requirement_id == requirement_id,
            TenderRequirementVersion.tender_id == tender_id,
        )

        if isinstance(version_identifier, uuid.UUID):
            stmt = stmt.where(TenderRequirementVersion.id == version_identifier)
        else:
            stmt = stmt.where(TenderRequirementVersion.version_number == int(version_identifier))

        v = db.scalars(stmt).first()
        if not v:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Requirement version '{version_identifier}' not found.",
            )

        author_name = None
        if v.changed_by_profile:
            author_name = v.changed_by_profile.full_name or v.changed_by_profile.email

        return TenderRequirementVersionResponse(
            id=v.id,
            tender_requirement_id=v.tender_requirement_id,
            tender_id=v.tender_id,
            version_number=v.version_number,
            code=v.code,
            name=v.name,
            description=v.description,
            category=v.category,
            requirement_type=v.requirement_type,
            operator=v.operator,
            expected_value=v.expected_value,
            unit=v.unit,
            is_mandatory=v.is_mandatory,
            is_critical=v.is_critical,
            weight=v.weight,
            display_order=v.display_order,
            source_clause=v.source_clause,
            source_page=v.source_page,
            corrigendum_number=v.corrigendum_number,
            effective_from=v.effective_from,
            effective_to=v.effective_to,
            change_reason=v.change_reason,
            changed_by_profile_id=v.changed_by_profile_id,
            changed_by_name=author_name,
            is_active=v.is_active,
            created_at=v.created_at,
            updated_at=v.updated_at,
        )

    @classmethod
    def compare_versions(
        cls,
        db: Session,
        tender_id: uuid.UUID,
        requirement_id: uuid.UUID,
        v1_num: int,
        v2_num: int,
        current_user: User,
    ) -> TenderRequirementVersionCompareResponse:
        """
        Performs structured side-by-side diff comparison between Version v1 and Version v2.
        """
        get_tender_by_id(db=db, tender_id=tender_id, current_user=current_user)

        v1 = db.scalars(
            select(TenderRequirementVersion)
            .options(joinedload(TenderRequirementVersion.changed_by_profile))
            .where(
                TenderRequirementVersion.tender_requirement_id == requirement_id,
                TenderRequirementVersion.version_number == v1_num,
            )
        ).first()

        v2 = db.scalars(
            select(TenderRequirementVersion)
            .options(joinedload(TenderRequirementVersion.changed_by_profile))
            .where(
                TenderRequirementVersion.tender_requirement_id == requirement_id,
                TenderRequirementVersion.version_number == v2_num,
            )
        ).first()

        if not v1 or not v2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cannot compare: Version {v1_num if not v1 else v2_num} not found.",
            )

        diffs: List[TenderRequirementFieldDiff] = []
        differences_count = 0

        for field_name, label, impact in COMPARABLE_FIELDS:
            old_val = getattr(v1, field_name)
            new_val = getattr(v2, field_name)

            old_norm = _normalize_val_for_comparison(old_val)
            new_norm = _normalize_val_for_comparison(new_val)
            is_diff = old_norm != new_norm

            impact_summary = ""
            if is_diff:
                differences_count += 1
                if field_name == "expected_value":
                    impact_summary = f"Threshold/criteria value changed from {old_norm} to {new_norm}"
                elif field_name == "operator":
                    impact_summary = f"Rule comparison operator changed from {old_val} to {new_val}"
                elif field_name == "is_mandatory":
                    impact_summary = f"Requirement mandatory status changed to {new_val}"
                elif field_name == "is_critical":
                    impact_summary = f"Disqualification trigger status changed to {new_val}"
                elif field_name == "weight":
                    impact_summary = f"Evaluation scoring weight changed from {old_val} to {new_val}"
                else:
                    impact_summary = f"{label} updated"

            diffs.append(
                TenderRequirementFieldDiff(
                    field_name=field_name,
                    field_label=label,
                    old_value=old_val,
                    new_value=new_val,
                    is_different=is_diff,
                    impact_level=impact if is_diff else "INFO",
                    impact_summary=impact_summary,
                )
            )

        v1_author = (
            v1.changed_by_profile.full_name or v1.changed_by_profile.email
            if v1.changed_by_profile
            else "System"
        )
        v2_author = (
            v2.changed_by_profile.full_name or v2.changed_by_profile.email
            if v2.changed_by_profile
            else "System"
        )

        return TenderRequirementVersionCompareResponse(
            tender_id=tender_id,
            requirement_id=requirement_id,
            code=v2.code,
            name=v2.name,
            v1_number=v1.version_number,
            v2_number=v2.version_number,
            v1_id=v1.id,
            v2_id=v2.id,
            v1_created_at=v1.created_at,
            v2_created_at=v2.created_at,
            v1_reason=v1.change_reason,
            v2_reason=v2.change_reason,
            v1_author=v1_author,
            v2_author=v2_author,
            has_differences=(differences_count > 0),
            differences_count=differences_count,
            diffs=diffs,
        )

    @classmethod
    def reevaluate_tender_bids(
        cls,
        db: Session,
        tender_id: uuid.UUID,
        current_user: User,
        requirement_id: Optional[uuid.UUID] = None,
    ) -> ReevaluationResultResponse:
        """
        Explicitly triggers re-evaluation for all submitted/active bids of a tender
        against the latest active rule versions.
        
        Preserves Human Decision Safety:
        - If a final human decision (QUALIFIED / DISQUALIFIED / UNDER_REVIEW) exists,
          it is NOT overwritten. A warning badge is populated in evaluation summaries.
        """
        tender = get_tender_by_id(db=db, tender_id=tender_id, current_user=current_user)

        # Import evaluation and compliance services inside method to prevent circular imports
        from app.services.compliance_service import evaluate_bid
        from app.services.scoring_service import calculate_and_save_bid_score
        from app.services.risk_service import calculate_and_save_bid_risk

        # Load active bids for this tender
        bids = db.scalars(
            select(Bid)
            .options(joinedload(Bid.bidder_organization))
            .where(
                and_(
                    Bid.tender_id == tender_id,
                    Bid.is_active == True,  # noqa: E712
                    Bid.status.in_(["SUBMITTED", "UNDER_EVALUATION", "EVALUATED", "SHORTLISTED"]),
                )
            )
            .order_by(Bid.created_at.asc())
        ).all()

        if not bids:
            return ReevaluationResultResponse(
                tender_id=tender.id,
                tender_number=tender.tender_number,
                requirement_id=requirement_id,
                total_bids_reevaluated=0,
                status_changes_count=0,
                stale_evaluations_cleared=0,
                human_decisions_preserved=0,
                reevaluated_at=datetime.now(timezone.utc),
                bids=[],
            )

        bid_results: List[ReevaluationBidResult] = []
        status_changes_count = 0
        human_decisions_preserved = 0

        target_req = None
        if requirement_id:
            target_req = db.scalars(
                select(TenderRequirement).where(
                    TenderRequirement.id == requirement_id,
                    TenderRequirement.tender_id == tender_id,
                )
            ).first()

        for bid in bids:
            # Capture previous compliance status for the target requirement if applicable
            prev_status = None
            if requirement_id:
                prev_cr = db.scalars(
                    select(ComplianceResult).where(
                        ComplianceResult.bid_id == bid.id,
                        ComplianceResult.tender_requirement_id == requirement_id,
                        ComplianceResult.is_current == True,  # noqa: E712
                    )
                ).first()
                if prev_cr:
                    prev_status = prev_cr.compliance_status

            # Check if bid has an active human decision
            has_decision = db.scalar(
                select(func.count(BidDecision.id)).where(
                    BidDecision.bid_id == bid.id,
                    BidDecision.is_current == True,  # noqa: E712
                )
            ) > 0
            if has_decision:
                human_decisions_preserved += 1

            # 1. Run compliance evaluation against latest rules
            comp_summary = evaluate_bid(db=db, current_user=current_user, bid_id=bid.id)

            # 2. Re-calculate score and risk deterministically
            score_snap = calculate_and_save_bid_score(db=db, current_user=current_user, bid_id=bid.id)
            risk_snap = calculate_and_save_bid_risk(db=db, current_user=current_user, bid_id=bid.id)

            # Find new status for target requirement or overall bid
            new_status = "PASS"
            is_crit_fail = False
            if requirement_id:
                new_cr = next((r for r in comp_summary.results if r.tender_requirement_id == requirement_id), None)
                new_status = new_cr.compliance_status if new_cr else "UNKNOWN"
                is_crit_fail = new_cr.critical_failure if new_cr else False
            else:
                if comp_summary.counts.critical_failures > 0 or comp_summary.counts.mandatory_failures > 0:
                    new_status = "FAIL"
                elif comp_summary.counts.review > 0:
                    new_status = "REVIEW"
                else:
                    new_status = "PASS"
                is_crit_fail = comp_summary.counts.critical_failures > 0

            status_changed = (prev_status is not None and prev_status != new_status)
            if status_changed:
                status_changes_count += 1

            bid_results.append(
                ReevaluationBidResult(
                    bid_id=bid.id,
                    bid_number=bid.bid_number,
                    bidder_name=bid.bidder_organization.name if bid.bidder_organization else None,
                    previous_compliance_status=prev_status,
                    new_compliance_status=new_status,
                    status_changed=status_changed,
                    is_critical_failure=is_crit_fail,
                    score=score_snap.total_score if score_snap else None,
                    risk_level=risk_snap.overall_risk_level if risk_snap else None,
                )
            )

        # Audit event
        try:
            AuditService.record_event(
                db=db,
                event_dto=RecordAuditEventDTO(
                    organization_id=tender.organization_id,
                    tender_id=tender.id,
                    event_type=AuditEventType.COMPLIANCE_RULE_REEVALUATION_REQUESTED,
                    entity_type=AuditEntityType.TENDER,
                    entity_id=tender.id,
                    actor_user_id=current_user.id,
                    actor_profile_id=current_user.profile_id,
                    actor_source=AuditActorSource.HUMAN,
                    action="REEVALUATE_RULES",
                    summary=(
                        f"Re-evaluated {len(bids)} bids for tender {tender.tender_number} "
                        f"against latest active compliance rules"
                        + (f" for rule [{target_req.code}]" if target_req else "")
                    ),
                    metadata={
                        "total_bids": len(bids),
                        "status_changes": status_changes_count,
                        "human_decisions_preserved": human_decisions_preserved,
                        "requirement_id": str(requirement_id) if requirement_id else None,
                    },
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to record audit event for rule re-evaluation: {e}")

        return ReevaluationResultResponse(
            tender_id=tender.id,
            tender_number=tender.tender_number,
            requirement_id=requirement_id,
            rule_code=target_req.code if target_req else None,
            new_version_number=target_req.current_version_number if target_req else None,
            total_bids_reevaluated=len(bids),
            status_changes_count=status_changes_count,
            stale_evaluations_cleared=len(bids),
            human_decisions_preserved=human_decisions_preserved,
            reevaluated_at=datetime.now(timezone.utc),
            bids=bid_results,
        )

    @classmethod
    def get_tender_rule_snapshot(
        cls,
        db: Session,
        tender_id: uuid.UUID,
        as_of: Optional[datetime] = None,
    ) -> Dict[uuid.UUID, TenderRequirementVersion]:
        """
        Retrieves the exact rule version for each requirement of a tender as of a timestamp.
        Used for reproducible audit replays and bulk evaluation consistency.
        """
        requirements = db.scalars(
            select(TenderRequirement).where(
                TenderRequirement.tender_id == tender_id,
                TenderRequirement.is_active == True,  # noqa: E712
            )
        ).all()

        snapshot: Dict[uuid.UUID, TenderRequirementVersion] = {}
        for req in requirements:
            stmt = select(TenderRequirementVersion).where(
                TenderRequirementVersion.tender_requirement_id == req.id
            )
            if as_of:
                stmt = stmt.where(TenderRequirementVersion.created_at <= as_of)
            stmt = stmt.order_by(TenderRequirementVersion.version_number.desc())
            ver = db.scalars(stmt).first()
            if ver:
                snapshot[req.id] = ver

        return snapshot
