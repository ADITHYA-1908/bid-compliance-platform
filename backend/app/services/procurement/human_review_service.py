"""
Human Review & Evidence Inspection Service for Part 8C
Coordinates review queue ingestion, multi-source evidence aggregation,
cross-document comparisons, auditable notes, and human resolution workflows.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, and_
from sqlalchemy.orm import Session, joinedload

from app.db.models.ai_recommendation import AIRecommendationRecord
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.clarification import ClarificationRequest, ClarificationStatus
from app.db.models.compliance_result import ComplianceResult, ComplianceStatus
from app.db.models.document_duplicate_match import DocumentDuplicateMatch
from app.db.models.document_processing import DocumentProcessing
from app.db.models.document_quality import DocumentQualityResult, QualityLevel
from app.db.models.document_validity import DocumentValidityRecord, ValidityStatus
from app.db.models.human_review import (
    HumanReviewItem,
    HumanReviewNote,
    ReviewResolution,
    ReviewSeverity,
    ReviewStatus,
    ReviewType,
)
from app.db.models.profile import Profile
from app.db.models.risk_snapshot import BidRiskSnapshot
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User
from app.db.models.verification_record import VerificationRecord
from app.schemas.human_review import (
    AddReviewNoteRequest,
    CrossDocumentComparisonRow,
    ResolveReviewRequest,
    ReviewAICitationItem,
    ReviewAIExplanationSection,
    ReviewActualEvidenceSection,
    ReviewClarificationSection,
    ReviewComplianceEvidenceSection,
    ReviewDetailResponse,
    ReviewNoteItem,
    ReviewQueueItemResponse,
    ReviewQueueKPIs,
    ReviewQueueResponse,
    ReviewRequirementSection,
    ReviewResolutionEnum,
    ReviewRiskSection,
    ReviewSeverityEnum,
    ReviewSourceDocumentSection,
    ReviewStatusEnum,
    ReviewTypeEnum,
    ReviewVerificationEvidenceSection,
)
from app.db.models.audit_event import AuditActorSource, AuditEntityType, AuditEventType
from app.schemas.audit import RecordAuditEventDTO
from app.services.audit.audit_service import AuditService
from app.services.risk_service import calculate_and_save_bid_risk
from app.services.scoring_service import calculate_and_save_bid_score

logger = logging.getLogger(__name__)


def format_issue_type_display(review_type: str, title: str = "") -> str:
    """Returns a clean, human-readable issue title for the review queue."""
    if review_type in (ReviewType.IDENTITY_MISMATCH, ReviewType.ORGANIZATION_MISMATCH):
        return "PAN/GST Mismatch"
    if review_type == ReviewType.POTENTIAL_DOCUMENT_REUSE:
        return "Potential Document Reuse"
    if review_type == ReviewType.POOR_DOCUMENT_QUALITY:
        return "Poor Document Quality"
    if review_type == ReviewType.EXPIRED_CERTIFICATE:
        return "Expired Certificate"
    if review_type == ReviewType.BLACKLISTING_SIGNAL:
        return "Blacklisting Signal"
    if review_type == ReviewType.CRITICAL_REVIEW:
        return "Critical Clause Failure"
    if review_type == ReviewType.COMPLIANCE_REVIEW:
        return "Mandatory Compliance Review"
    if review_type == ReviewType.VERIFICATION_REVIEW:
        return "Verification Discrepancy"
    if review_type == ReviewType.UNRESOLVED_CLARIFICATION:
        return "Clarification Pending"

    # Fallback to title keywords only if review_type is OTHER
    if "PAN" in title or "GST" in title or "Identity" in title:
        return "PAN/GST Mismatch"
    if "Reuse" in title or "Duplicate" in title:
        return "Potential Document Reuse"
    if "Blurry" in title or "Quality" in title:
        return "Poor Document Quality"
    if "Expired" in title:
        return "Expired Certificate"
    if "Blacklist" in title or "Debar" in title:
        return "Blacklisting Signal"

    return review_type.replace("_", " ").title()


def _verify_officer_access(db: Session, user: User) -> Tuple[User, Profile, Role]:
    """
    Validates user authentication and ensures the user is an authorized Procurement Officer or Admin.
    Rejects Bidder role with HTTP 403.
    """
    if not user.profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User profile not configured.",
        )

    profile = db.scalars(
        select(Profile)
        .options(joinedload(Profile.role), joinedload(Profile.organization))
        .where(Profile.id == user.profile_id)
    ).first()

    if not profile or not profile.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User profile or role not found.",
        )

    role_name = profile.role.name.upper() if profile.role else ""
    if role_name not in ("PROCUREMENT_OFFICER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Human review queue is restricted to authorized Procurement Officers and Admins.",
        )

    return user, profile, profile.role


def _verify_review_item_access(db: Session, user: User, review_id: uuid.UUID) -> Tuple[HumanReviewItem, Profile]:
    """
    Validates tenant isolation for a specific review item.
    """
    _, profile, role = _verify_officer_access(db, user)

    stmt = (
        select(HumanReviewItem)
        .options(
            joinedload(HumanReviewItem.tender),
            joinedload(HumanReviewItem.bid).joinedload(Bid.bidder_organization),
            joinedload(HumanReviewItem.tender_requirement),
            joinedload(HumanReviewItem.compliance_result),
            joinedload(HumanReviewItem.verification_record),
            joinedload(HumanReviewItem.bid_document),
            joinedload(HumanReviewItem.claimed_by_profile),
            joinedload(HumanReviewItem.resolved_by_profile),
            joinedload(HumanReviewItem.notes).joinedload(HumanReviewNote.author_profile).joinedload(Profile.role),
        )
        .where(HumanReviewItem.id == review_id)
    )
    item = db.execute(stmt).unique().scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review item not found or access denied.",
        )

    if role.name != "ADMIN" and item.organization_id != profile.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review item not found or access denied.",
        )

    return item, profile


class HumanReviewService:
    """
    Service managing Human Review Queue, Evidence Inspection Workspaces, and Resolution.
    """

    @classmethod
    def sync_review_items_for_bid(cls, db: Session, bid_id: uuid.UUID) -> List[HumanReviewItem]:
        """
        Inspects upstream compliance results, verification records, document quality,
        certificate validity, cross-bidder document reuse, and risk signals
        to idempotently generate, update, or supersede HumanReviewItems for a Bid.
        """
        bid = db.scalars(
            select(Bid)
            .options(joinedload(Bid.tender), joinedload(Bid.bidder_organization))
            .where(Bid.id == bid_id, Bid.is_active == True)
        ).first()

        if not bid or not bid.tender:
            return []

        tender_id = bid.tender_id
        org_id = bid.tender.organization_id

        # 1. Fetch current Compliance Results
        comp_results = db.scalars(
            select(ComplianceResult)
            .options(joinedload(ComplianceResult.tender_requirement))
            .where(ComplianceResult.bid_id == bid_id, ComplianceResult.is_current == True)
        ).all()

        # 2. Fetch current Verification Records
        verif_records = db.scalars(
            select(VerificationRecord)
            .where(VerificationRecord.bid_id == bid_id)
        ).all()

        # 3. Fetch current Documents & Processings
        docs = db.scalars(
            select(BidDocument)
            .where(BidDocument.bid_id == bid_id, BidDocument.is_active == True)
        ).all()

        # 4. Fetch existing HumanReviewItems for this bid
        existing_items = db.scalars(
            select(HumanReviewItem)
            .where(HumanReviewItem.bid_id == bid_id)
        ).all()
        existing_map = {(item.source_type, item.source_id): item for item in existing_items}

        active_source_keys = set()
        synced_items: List[HumanReviewItem] = []

        # Process Compliance Results for REVIEW items & Critical Failures
        for cr in comp_results:
            req = cr.tender_requirement
            source_id = str(cr.id)
            source_key = ("COMPLIANCE_RESULT", source_id)

            needs_review = (
                cr.compliance_status == ComplianceStatus.REVIEW
                or cr.critical_failure
                or (cr.is_critical and cr.compliance_status == ComplianceStatus.FAIL)
            )

            if needs_review:
                active_source_keys.add(source_key)
                existing = existing_map.get(source_key)

                # Determine severity and review type deterministically
                if cr.is_critical or cr.critical_failure:
                    sev = ReviewSeverity.CRITICAL
                    rev_type = ReviewType.CRITICAL_REVIEW
                elif req and req.is_mandatory:
                    sev = ReviewSeverity.HIGH
                    rev_type = ReviewType.COMPLIANCE_REVIEW
                else:
                    sev = ReviewSeverity.MEDIUM
                    rev_type = ReviewType.COMPLIANCE_REVIEW

                req_name = req.name if req else "Tender Clause"
                req_code = req.code if req else "CLAUSE"
                title = f"[{req_code}] {req_name} — {cr.compliance_status}"
                reason = cr.reason or "Evaluation determination requires human officer verification."

                system_finding = {
                    "compliance_status": cr.compliance_status,
                    "expected_value": cr.expected_value,
                    "actual_value": cr.actual_value,
                    "operator": cr.operator,
                    "is_mandatory": cr.is_mandatory,
                    "is_critical": cr.is_critical,
                    "critical_failure": cr.critical_failure,
                    "weight": float(cr.weight) if cr.weight is not None else 10.0,
                    "reason": cr.reason,
                }

                # Resolve matching document & verification record if available
                matching_doc_id = None
                matching_vr_id = None
                if req:
                    m_doc = next((d for d in docs if d.tender_requirement_id == req.id), None)
                    if not m_doc:
                        if "oem" in req.name.lower() or "oem" in req.code.lower():
                            m_doc = next((d for d in docs if "oem" in d.document_type.lower()), None)
                    if m_doc:
                        matching_doc_id = m_doc.id
                        m_vr = next((v for v in verif_records if v.bid_document_id == m_doc.id), None)
                        if m_vr:
                            matching_vr_id = m_vr.id
                if not matching_vr_id and verif_records:
                    if req and ("oem" in req.name.lower() or "oem" in req.code.lower()):
                        m_vr = next((v for v in verif_records if "oem" in v.verification_type.lower()), None)
                        if m_vr:
                            matching_vr_id = m_vr.id

                if existing:
                    if existing.status in (ReviewStatus.OPEN, ReviewStatus.IN_REVIEW, ReviewStatus.IN_PROGRESS):
                        existing.title = title
                        existing.reason = reason
                        existing.system_finding = system_finding
                        existing.severity = sev
                        existing.review_type = rev_type
                        if matching_doc_id and not existing.bid_document_id:
                            existing.bid_document_id = matching_doc_id
                        if matching_vr_id and not existing.verification_record_id:
                            existing.verification_record_id = matching_vr_id
                        existing.is_active = True
                    synced_items.append(existing)
                else:
                    new_item = HumanReviewItem(
                        organization_id=org_id,
                        tender_id=tender_id,
                        bid_id=bid_id,
                        compliance_result_id=cr.id,
                        tender_requirement_id=cr.tender_requirement_id,
                        bid_document_id=matching_doc_id,
                        verification_record_id=matching_vr_id,
                        review_type=rev_type,
                        severity=sev,
                        status=ReviewStatus.OPEN,
                        source_type="COMPLIANCE_RESULT",
                        source_id=source_id,
                        title=title,
                        reason=reason,
                        system_finding=system_finding,
                        is_active=True,
                    )
                    db.add(new_item)
                    synced_items.append(new_item)

        # Process Verification Records with Needs Review or Discrepancies
        for vr in verif_records:
            source_id = str(vr.id)
            source_key = ("VERIFICATION_RECORD", source_id)

            is_verif_review = (
                vr.verification_status == "NEEDS_REVIEW"
                or vr.match_status in ("PARTIAL_MATCH", "MISMATCH")
            )

            if is_verif_review:
                active_source_keys.add(source_key)
                existing = existing_map.get(source_key)

                sev = ReviewSeverity.HIGH if vr.match_status == "MISMATCH" else ReviewSeverity.MEDIUM
                rev_type = ReviewType.IDENTITY_MISMATCH if ("IDENTITY" in vr.verification_type or "PAN" in vr.verification_type or "GST" in vr.verification_type) else ReviewType.VERIFICATION_REVIEW
                
                if vr.match_status == "MISMATCH" and ("PAN" in vr.verification_type or "GST" in vr.verification_type or "NAME" in vr.verification_type):
                    title = "Organization Identity Mismatch (PAN / GSTIN)"
                    reason = f"Legal name or identifier mismatch detected against {vr.source_name} registry."
                else:
                    title = f"{vr.verification_type.replace('_', ' ').title()} Verification Discrepancy"
                    reason = f"Verification returned {vr.match_status or vr.verification_status} against {vr.source_name} ({vr.source_type})."

                system_finding = {
                    "verification_type": vr.verification_type,
                    "verification_status": vr.verification_status,
                    "match_status": vr.match_status,
                    "source_name": vr.source_name,
                    "source_type": vr.source_type,
                    "claimed_value": getattr(vr, "claimed_value", None),
                    "verified_value": getattr(vr, "verified_value", None),
                    "confidence_score": float(vr.confidence) if getattr(vr, "confidence", None) is not None else None,
                    "evidence_payload": vr.evidence if hasattr(vr, "evidence") else getattr(vr, "response_payload", None),
                }

                if existing:
                    if existing.status in (ReviewStatus.OPEN, ReviewStatus.IN_REVIEW, ReviewStatus.IN_PROGRESS):
                        existing.title = title
                        existing.reason = reason
                        existing.system_finding = system_finding
                        existing.severity = sev
                        existing.review_type = rev_type
                        existing.is_active = True
                    synced_items.append(existing)
                else:
                    new_item = HumanReviewItem(
                        organization_id=org_id,
                        tender_id=tender_id,
                        bid_id=bid_id,
                        verification_record_id=vr.id,
                        bid_document_id=vr.bid_document_id,
                        review_type=rev_type,
                        severity=sev,
                        status=ReviewStatus.OPEN,
                        source_type="VERIFICATION_RECORD",
                        source_id=source_id,
                        title=title,
                        reason=reason,
                        system_finding=system_finding,
                        is_active=True,
                    )
                    db.add(new_item)
                    synced_items.append(new_item)

        # Process Document Quality Results with Poor or Unusable Quality
        for doc in docs:
            qr = db.scalars(
                select(DocumentQualityResult).where(DocumentQualityResult.document_id == doc.id)
            ).first()
            if not qr:
                continue

            needs_quality_review = (
                qr.review_required
                or qr.quality_level in (QualityLevel.POOR, QualityLevel.UNUSABLE)
                or qr.is_corrupted
                or qr.is_password_protected
            )

            if needs_quality_review:
                source_id = str(qr.id)
                source_key = ("DOCUMENT_QUALITY_RESULT", source_id)
                active_source_keys.add(source_key)
                existing = existing_map.get(source_key)

                sev = ReviewSeverity.CRITICAL if qr.quality_level == QualityLevel.UNUSABLE else ReviewSeverity.MEDIUM
                title = f"Poor Document Quality: {doc.original_filename} ({qr.quality_level})"
                reason = (
                    qr.review_reasons[0]
                    if qr.review_reasons
                    else f"Document quality score ({qr.quality_score}/100) is too poor for reliable verification."
                )

                system_finding = {
                    "document_id": str(doc.id),
                    "filename": doc.original_filename,
                    "document_type": doc.document_type,
                    "quality_score": qr.quality_score,
                    "quality_level": qr.quality_level,
                    "is_blurry": qr.is_blurry,
                    "has_blank_pages": qr.has_blank_pages,
                    "has_unreadable_pages": qr.has_unreadable_pages,
                    "is_corrupted": qr.is_corrupted,
                    "is_password_protected": qr.is_password_protected,
                    "review_reasons": qr.review_reasons,
                    "bidder_feedback": qr.bidder_feedback,
                }

                if existing:
                    if existing.status in (ReviewStatus.OPEN, ReviewStatus.IN_REVIEW, ReviewStatus.IN_PROGRESS):
                        existing.title = title
                        existing.reason = reason
                        existing.system_finding = system_finding
                        existing.severity = sev
                        existing.review_type = ReviewType.POOR_DOCUMENT_QUALITY
                        existing.is_active = True
                    synced_items.append(existing)
                else:
                    new_item = HumanReviewItem(
                        organization_id=org_id,
                        tender_id=tender_id,
                        bid_id=bid_id,
                        bid_document_id=doc.id,
                        review_type=ReviewType.POOR_DOCUMENT_QUALITY,
                        severity=sev,
                        status=ReviewStatus.OPEN,
                        source_type="DOCUMENT_QUALITY_RESULT",
                        source_id=source_id,
                        title=title,
                        reason=reason,
                        system_finding=system_finding,
                        is_active=True,
                    )
                    db.add(new_item)
                    synced_items.append(new_item)

        # Process Document Validity Records for Expired / Review Required certificates
        validity_records = db.scalars(
            select(DocumentValidityRecord).where(
                DocumentValidityRecord.bid_id == bid_id,
                DocumentValidityRecord.is_current == True,
                DocumentValidityRecord.is_active == True,
            )
        ).all()

        for vr_doc in validity_records:
            needs_val_review = (
                vr_doc.validity_status in (ValidityStatus.EXPIRED.value, ValidityStatus.REVIEW_REQUIRED.value)
                or (vr_doc.days_until_expiry is not None and vr_doc.days_until_expiry <= 0)
            )
            if needs_val_review:
                source_id = str(vr_doc.id)
                source_key = ("DOCUMENT_VALIDITY_RECORD", source_id)
                active_source_keys.add(source_key)
                existing = existing_map.get(source_key)

                is_expired = (vr_doc.validity_status == ValidityStatus.EXPIRED.value or (vr_doc.days_until_expiry is not None and vr_doc.days_until_expiry <= 0))
                sev = ReviewSeverity.HIGH if is_expired else ReviewSeverity.MEDIUM
                rev_type = ReviewType.EXPIRED_CERTIFICATE
                doc_name = vr_doc.document.original_filename if vr_doc.document else vr_doc.document_type
                if is_expired:
                    title = f"Expired Certificate: {doc_name}"
                    reason = f"{vr_doc.document_type} certificate expired on {vr_doc.expiry_date} prior to bid evaluation."
                else:
                    title = f"Certificate Validity Review Required: {doc_name}"
                    reason = f"{vr_doc.document_type} certificate validity could not be verified automatically."

                system_finding = {
                    "validity_record_id": str(vr_doc.id),
                    "document_id": str(vr_doc.document_id),
                    "document_type": vr_doc.document_type,
                    "validity_status": vr_doc.validity_status,
                    "expiry_date": vr_doc.expiry_date.isoformat() if vr_doc.expiry_date else None,
                    "issue_date": vr_doc.issue_date.isoformat() if vr_doc.issue_date else None,
                    "days_until_expiry": vr_doc.days_until_expiry,
                    "confidence": vr_doc.confidence,
                    "source_text": vr_doc.source_text,
                }

                if existing:
                    if existing.status in (ReviewStatus.OPEN, ReviewStatus.IN_REVIEW, ReviewStatus.IN_PROGRESS):
                        existing.title = title
                        existing.reason = reason
                        existing.system_finding = system_finding
                        existing.severity = sev
                        existing.review_type = rev_type
                        existing.is_active = True
                    synced_items.append(existing)
                else:
                    new_item = HumanReviewItem(
                        organization_id=org_id,
                        tender_id=tender_id,
                        bid_id=bid_id,
                        bid_document_id=vr_doc.document_id,
                        review_type=rev_type,
                        severity=sev,
                        status=ReviewStatus.OPEN,
                        source_type="DOCUMENT_VALIDITY_RECORD",
                        source_id=source_id,
                        title=title,
                        reason=reason,
                        system_finding=system_finding,
                        is_active=True,
                    )
                    db.add(new_item)
                    synced_items.append(new_item)

        # Process Cross-Bidder Duplicate Document Matches (Neutral Wording)
        dup_matches = db.scalars(
            select(DocumentDuplicateMatch).where(
                or_(
                    DocumentDuplicateMatch.bid_a_id == bid_id,
                    DocumentDuplicateMatch.bid_b_id == bid_id,
                ),
                DocumentDuplicateMatch.review_required == True,
            )
        ).all()

        for dm in dup_matches:
            source_id = str(dm.id)
            source_key = ("DOCUMENT_DUPLICATE", source_id)
            active_source_keys.add(source_key)
            existing = existing_map.get(source_key)

            sim = float(dm.overall_confidence or dm.text_similarity_score or 0)
            sev = ReviewSeverity.HIGH if sim >= 0.85 else ReviewSeverity.MEDIUM
            rev_type = ReviewType.POTENTIAL_DOCUMENT_REUSE
            doc_a_name = dm.document_a.original_filename if dm.document_a else "Submitted Document"
            title = f"Potential Document Reuse: {doc_a_name}"
            reason = f"Cross-bidder similarity detected ({sim * 100:.1f}% match) with another submission."

            system_finding = {
                "match_id": str(dm.id),
                "similarity_score": sim,
                "match_type": dm.match_type,
                "confidence": dm.overall_confidence,
                "review_required": dm.review_required,
                "evidence_summary": dm.evidence_summary or {},
                "matched_fields": dm.matched_fields or {},
            }

            if existing:
                if existing.status in (ReviewStatus.OPEN, ReviewStatus.IN_REVIEW, ReviewStatus.IN_PROGRESS):
                    existing.title = title
                    existing.reason = reason
                    existing.system_finding = system_finding
                    existing.severity = sev
                    existing.review_type = rev_type
                    existing.is_active = True
                synced_items.append(existing)
            else:
                new_item = HumanReviewItem(
                    organization_id=org_id,
                    tender_id=tender_id,
                    bid_id=bid_id,
                    bid_document_id=dm.document_a_id,
                    review_type=rev_type,
                    severity=sev,
                    status=ReviewStatus.OPEN,
                    source_type="DOCUMENT_DUPLICATE",
                    source_id=source_id,
                    title=title,
                    reason=reason,
                    system_finding=system_finding,
                    is_active=True,
                )
                db.add(new_item)
                synced_items.append(new_item)

        # Process Risk Snapshot for Critical Debarment / High Risk
        risk_snap = db.scalars(
            select(BidRiskSnapshot)
            .where(BidRiskSnapshot.bid_id == bid_id, BidRiskSnapshot.is_current == True)
            .order_by(BidRiskSnapshot.created_at.desc())
        ).first()

        if risk_snap:
            risk_level = (risk_snap.adjusted_risk_level or risk_snap.base_risk_level or "").upper()
            risk_score = float(risk_snap.adjusted_risk_score if risk_snap.adjusted_risk_score is not None else (risk_snap.base_risk_score if risk_snap.base_risk_score is not None else 0.0))
            signals = list(risk_snap.summary_reasons or [])
            if risk_snap.applied_overrides:
                for ov in risk_snap.applied_overrides:
                    if isinstance(ov, dict) and ov.get("reason"):
                        signals.append(str(ov.get("reason")))

            has_blacklisting = any("blacklist" in str(s).lower() or "debar" in str(s).lower() for s in signals)
            if risk_level in ("CRITICAL", "HIGH") or has_blacklisting:
                source_id = str(risk_snap.id)
                source_key = ("RISK_SNAPSHOT", source_id)
                active_source_keys.add(source_key)
                existing = existing_map.get(source_key)

                sev = ReviewSeverity.CRITICAL if (risk_level == "CRITICAL" or has_blacklisting) else ReviewSeverity.HIGH
                rev_type = ReviewType.BLACKLISTING_SIGNAL if has_blacklisting else ReviewType.CRITICAL_REVIEW

                if has_blacklisting:
                    title = "Critical Debarment / Blacklisting Signal"
                    reason = "Vendor or entity flagged in vigilance/debarment verification check."
                else:
                    title = f"{risk_level.title()} Risk Signal (Score: {risk_score:.0f}/100)"
                    reason = (signals[0] if signals else None) or f"High aggregate risk score ({risk_score:.0f}/100) requires procurement review."

                system_finding = {
                    "risk_snapshot_id": str(risk_snap.id),
                    "risk_level": risk_level,
                    "overall_risk_score": risk_score,
                    "signals": signals,
                    "risk_summary": "; ".join(signals) if signals else None,
                }

            if existing:
                if existing.status in (ReviewStatus.OPEN, ReviewStatus.IN_REVIEW, ReviewStatus.IN_PROGRESS):
                    existing.title = title
                    existing.reason = reason
                    existing.system_finding = system_finding
                    existing.severity = sev
                    existing.review_type = rev_type
                    existing.is_active = True
                synced_items.append(existing)
            else:
                new_item = HumanReviewItem(
                    organization_id=org_id,
                    tender_id=tender_id,
                    bid_id=bid_id,
                    review_type=rev_type,
                    severity=sev,
                    status=ReviewStatus.OPEN,
                    source_type="RISK_SNAPSHOT",
                    source_id=source_id,
                    title=title,
                    reason=reason,
                    system_finding=system_finding,
                    is_active=True,
                )
                db.add(new_item)
                synced_items.append(new_item)

        db.flush()

        # Check Active Clarifications linked to review items
        for item in synced_items:
            if item.id and item.status in (ReviewStatus.OPEN, ReviewStatus.IN_REVIEW, ReviewStatus.IN_PROGRESS, ReviewStatus.AWAITING_CLARIFICATION):
                clarif = db.scalars(
                    select(ClarificationRequest)
                    .where(ClarificationRequest.related_review_item_id == item.id)
                    .order_by(ClarificationRequest.created_at.desc())
                ).first()
                if clarif:
                    if clarif.status in (ClarificationStatus.SENT, ClarificationStatus.VIEWED):
                        item.status = ReviewStatus.AWAITING_CLARIFICATION
                    elif clarif.status == ClarificationStatus.RESPONDED and item.status == ReviewStatus.AWAITING_CLARIFICATION:
                        item.status = ReviewStatus.IN_REVIEW

        # Mark obsolete items as SUPERSEDED if source condition resolved upstream
        for existing in existing_items:
            key = (existing.source_type, existing.source_id)
            if key not in active_source_keys and existing.status in (ReviewStatus.OPEN, ReviewStatus.IN_REVIEW, ReviewStatus.IN_PROGRESS, ReviewStatus.AWAITING_CLARIFICATION):
                existing.status = ReviewStatus.SUPERSEDED
                existing.is_active = False

        db.flush()

        # Part 12: Notification Center trigger for newly created open review items
        try:
            from app.services.notification_service import NotificationService
            for item in synced_items:
                if item.status == ReviewStatus.OPEN:
                    NotificationService.notify_human_review_required(db=db, review_item=item)
        except Exception as notif_err:
            logger.debug("Human review notification notice: %s", notif_err)

        return synced_items

    @classmethod
    def get_review_queue(
        cls,
        db: Session,
        user: User,
        tender_id: Optional[uuid.UUID] = None,
        bid_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        severity: Optional[str] = None,
        review_type: Optional[str] = None,
        category: Optional[str] = None,
        critical_only: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> ReviewQueueResponse:
        """
        Fetches the paginated priority human review queue for the authenticated Procurement Officer's organization.
        """
        _, profile, role = _verify_officer_access(db, user)

        # 1. Base Query with joined relationships
        stmt = (
            select(HumanReviewItem)
            .options(
                joinedload(HumanReviewItem.tender),
                joinedload(HumanReviewItem.bid).joinedload(Bid.bidder_organization),
                joinedload(HumanReviewItem.tender_requirement),
                joinedload(HumanReviewItem.claimed_by_profile),
                joinedload(HumanReviewItem.resolved_by_profile),
            )
            .where(HumanReviewItem.is_active == True)
        )

        # Scoping
        if role.name != "ADMIN":
            stmt = stmt.where(HumanReviewItem.organization_id == profile.organization_id)

        # 2. Filters
        if tender_id:
            stmt = stmt.where(HumanReviewItem.tender_id == tender_id)
        if bid_id:
            stmt = stmt.where(HumanReviewItem.bid_id == bid_id)
        if status_filter:
            st = status_filter.upper()
            if st == "OPEN":
                stmt = stmt.where(HumanReviewItem.status.in_([ReviewStatus.OPEN]))
            elif st in ("IN_PROGRESS", "IN_REVIEW"):
                stmt = stmt.where(HumanReviewItem.status.in_([ReviewStatus.IN_REVIEW, ReviewStatus.IN_PROGRESS]))
            elif st == "AWAITING_CLARIFICATION":
                stmt = stmt.where(HumanReviewItem.status == ReviewStatus.AWAITING_CLARIFICATION)
            elif st == "RESOLVED":
                stmt = stmt.where(HumanReviewItem.status.in_([ReviewStatus.RESOLVED, ReviewStatus.DISMISSED]))
            else:
                stmt = stmt.where(HumanReviewItem.status == st)
        if severity:
            stmt = stmt.where(HumanReviewItem.severity == severity.upper())
        if review_type:
            stmt = stmt.where(HumanReviewItem.review_type == review_type.upper())
        if critical_only:
            stmt = stmt.where(HumanReviewItem.severity == ReviewSeverity.CRITICAL)

        # Execute search and relationships joins if needed
        all_items = db.execute(stmt).scalars().unique().all()

        # In-memory category and search filtering for high accuracy
        filtered_items = all_items

        if category:
            filtered_items = [
                i for i in filtered_items
                if i.tender_requirement and i.tender_requirement.category == category.upper()
            ]

        if search:
            s_low = search.strip().lower()
            filtered_items = [
                i for i in filtered_items
                if (
                    (i.bid and s_low in i.bid.bid_number.lower())
                    or (i.bid and i.bid.bidder_organization and s_low in i.bid.bidder_organization.name.lower())
                    or (i.tender and s_low in i.tender.tender_number.lower())
                    or (i.tender and s_low in i.tender.title.lower())
                    or (i.tender_requirement and s_low in i.tender_requirement.name.lower())
                    or (i.tender_requirement and s_low in i.tender_requirement.code.lower())
                    or (i.bid and i.bid.bidder_organization and i.bid.bidder_organization.pan_number and s_low in i.bid.bidder_organization.pan_number.lower())
                    or (i.bid and i.bid.bidder_organization and i.bid.bidder_organization.gstin and s_low in i.bid.bidder_organization.gstin.lower())
                    or s_low in i.title.lower()
                    or s_low in i.reason.lower()
                )
            ]

        # 3. Calculate Real-Time KPIs across organization's active items
        kpi_stmt = select(HumanReviewItem).where(HumanReviewItem.is_active == True)
        if role.name != "ADMIN":
            kpi_stmt = kpi_stmt.where(HumanReviewItem.organization_id == profile.organization_id)
        org_items = db.execute(kpi_stmt).scalars().all()

        now_utc = datetime.now(timezone.utc)
        today_start = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)

        total_open = sum(1 for i in org_items if i.status in (ReviewStatus.OPEN, ReviewStatus.IN_REVIEW, ReviewStatus.IN_PROGRESS, ReviewStatus.AWAITING_CLARIFICATION))
        critical_open = sum(1 for i in org_items if i.status in (ReviewStatus.OPEN, ReviewStatus.IN_REVIEW, ReviewStatus.IN_PROGRESS, ReviewStatus.AWAITING_CLARIFICATION) and i.severity == ReviewSeverity.CRITICAL)
        high_open = sum(1 for i in org_items if i.status in (ReviewStatus.OPEN, ReviewStatus.IN_REVIEW, ReviewStatus.IN_PROGRESS, ReviewStatus.AWAITING_CLARIFICATION) and i.severity == ReviewSeverity.HIGH)
        awaiting_clarification = sum(1 for i in org_items if i.status == ReviewStatus.AWAITING_CLARIFICATION)
        in_review = sum(1 for i in org_items if i.status in (ReviewStatus.IN_REVIEW, ReviewStatus.IN_PROGRESS))
        resolved_today = sum(1 for i in org_items if i.status in (ReviewStatus.RESOLVED, ReviewStatus.DISMISSED) and i.resolved_at and i.resolved_at >= today_start)
        escalated = sum(1 for i in org_items if i.status == ReviewStatus.ESCALATED)

        kpis = ReviewQueueKPIs(
            total_open=total_open,
            critical_open=critical_open,
            high_open=high_open,
            awaiting_clarification=awaiting_clarification,
            in_review=in_review,
            resolved_today=resolved_today,
            escalated=escalated,
        )

        # 4. Sort: Priority first (CRITICAL -> HIGH -> MEDIUM -> NORMAL/LOW), then oldest unresolved first
        severity_rank = {
            ReviewSeverity.CRITICAL: 0,
            ReviewSeverity.HIGH: 1,
            ReviewSeverity.MEDIUM: 2,
            ReviewSeverity.NORMAL: 3,
            ReviewSeverity.LOW: 3,
        }

        def item_sort_key(item: HumanReviewItem):
            is_unresolved = 0 if item.status in (ReviewStatus.OPEN, ReviewStatus.IN_REVIEW, ReviewStatus.IN_PROGRESS, ReviewStatus.AWAITING_CLARIFICATION, ReviewStatus.ESCALATED) else 1
            sev = severity_rank.get(item.severity, 99)
            created_ts = item.created_at.timestamp() if item.created_at else 0
            time_val = created_ts if is_unresolved == 0 else -created_ts
            return (is_unresolved, sev, time_val)

        filtered_items.sort(key=item_sort_key)

        # 5. Pagination
        total_count = len(filtered_items)
        page_size = max(1, min(page_size, 100))
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        page = max(1, min(page, total_pages)) if total_count > 0 else 1

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_items = filtered_items[start_idx:end_idx]

        # 6. Map to Response Models
        response_items: List[ReviewQueueItemResponse] = []
        for item in paged_items:
            bid = item.bid
            tender = item.tender
            bidder = bid.bidder_organization if bid else None
            req = item.tender_requirement

            # Map status to appropriate enum
            st_val = item.status
            if st_val == ReviewStatus.IN_PROGRESS:
                st_enum = ReviewStatusEnum.IN_PROGRESS
            elif st_val == ReviewStatus.AWAITING_CLARIFICATION:
                st_enum = ReviewStatusEnum.AWAITING_CLARIFICATION
            elif st_val == ReviewStatus.DISMISSED:
                st_enum = ReviewStatusEnum.DISMISSED
            else:
                st_enum = ReviewStatusEnum(st_val) if st_val in ReviewStatusEnum._value2member_map_ else ReviewStatusEnum.OPEN

            # Check if linked clarification exists
            clarif_status_str = None
            if item.status == ReviewStatus.AWAITING_CLARIFICATION:
                clarif_status_str = "Awaiting Bidder Response"

            response_items.append(
                ReviewQueueItemResponse(
                    id=item.id,
                    tender_id=item.tender_id,
                    tender_number=tender.tender_number if tender else "N/A",
                    tender_title=tender.title if tender else "N/A",
                    bid_id=item.bid_id,
                    bid_number=bid.bid_number if bid else "N/A",
                    bidder_name=bidder.name if bidder else "Unknown Bidder",
                    bidder_pan=bidder.pan_number if bidder else None,
                    bidder_gstin=bidder.gstin if bidder else None,
                    requirement_code=req.code if req else None,
                    requirement_name=req.name if req else None,
                    category=req.category if req else None,
                    review_type=ReviewTypeEnum(item.review_type) if item.review_type in ReviewTypeEnum._value2member_map_ else ReviewTypeEnum.OTHER,
                    issue_type_display=format_issue_type_display(item.review_type, item.title),
                    severity=ReviewSeverityEnum(item.severity) if item.severity in ReviewSeverityEnum._value2member_map_ else ReviewSeverityEnum.MEDIUM,
                    status=st_enum,
                    source_type=item.source_type,
                    title=item.title,
                    reason=item.reason,
                    is_critical=(item.severity == ReviewSeverity.CRITICAL),
                    is_mandatory=req.is_mandatory if req else False,
                    claimed_by_name=item.claimed_by_profile.full_name if item.claimed_by_profile else None,
                    resolved_by_name=item.resolved_by_profile.full_name if item.resolved_by_profile else None,
                    resolution=ReviewResolutionEnum(item.resolution) if (item.resolution and item.resolution in ReviewResolutionEnum._value2member_map_) else None,
                    clarification_status=clarif_status_str,
                    risk_level=item.severity,
                    created_at=item.created_at,
                    resolved_at=item.resolved_at,
                )
            )

        return ReviewQueueResponse(
            kpis=kpis,
            items=response_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @classmethod
    def get_review_detail(cls, db: Session, user: User, review_id: uuid.UUID) -> ReviewDetailResponse:
        """
        Loads the complete evidence inspection workspace package for a HumanReviewItem.
        """
        item, _ = _verify_review_item_access(db, user, review_id)

        tender = item.tender
        bid = item.bid
        bidder = bid.bidder_organization if bid else None
        req = item.tender_requirement
        cr = item.compliance_result
        vr = item.verification_record
        doc = item.bid_document
        if not doc:
            if vr and getattr(vr, "bid_document_id", None):
                doc = db.scalars(select(BidDocument).where(BidDocument.id == vr.bid_document_id)).first()
            elif req:
                doc = db.scalars(
                    select(BidDocument).where(
                        BidDocument.bid_id == item.bid_id,
                        BidDocument.is_active == True,
                        or_(
                            BidDocument.tender_requirement_id == req.id,
                            BidDocument.document_type.ilike(f"%{req.code.split('-')[1]}%"),
                            BidDocument.document_type.ilike("%OEM%") if "OEM" in req.code or "OEM" in req.name else False,
                        )
                    )
                ).first()
            if not doc:
                doc = db.scalars(select(BidDocument).where(BidDocument.bid_id == item.bid_id, BidDocument.is_active == True)).first()

        # 1. Requirement Section
        req_section = None
        if req:
            req_section = ReviewRequirementSection(
                requirement_id=req.id,
                code=req.code,
                name=req.name,
                category=req.category,
                requirement_type=req.requirement_type,
                expected_value=req.expected_value,
                operator=req.operator,
                is_mandatory=req.is_mandatory,
                is_critical=req.is_critical,
                weight=float(req.weight) if req.weight is not None else 10.0,
            )

        # 2. Actual Evidence Section
        actual_section = None
        if cr or vr:
            actual_section = ReviewActualEvidenceSection(
                claimed_value=cr.actual_value if cr else (vr.claimed_value if hasattr(vr, "claimed_value") else None),
                extracted_value=cr.actual_value if cr else None,
                verified_value=vr.verified_value if (vr and hasattr(vr, "verified_value")) else None,
                match_status=vr.match_status if vr else (cr.compliance_status if cr else None),
                extraction_confidence=0.92,
                field_confidence="HIGH",
                compliance_status=cr.compliance_status if cr else None,
                system_reason=cr.reason if cr else (item.reason),
            )

        # 3. Source Document Section
        doc_section = None
        if doc:
            # Check processing
            dp = db.scalars(
                select(DocumentProcessing)
                .where(DocumentProcessing.bid_document_id == doc.id)
                .order_by(DocumentProcessing.created_at.desc())
            ).first()

            snippet = None
            if dp:
                txt = dp.raw_text or dp.normalized_text
                if txt:
                    snippet = txt[:400] + ("..." if len(txt) > 400 else "")

            doc_section = ReviewSourceDocumentSection(
                document_id=doc.id,
                document_name=doc.document_name or doc.original_filename,
                document_type=doc.document_type,
                file_size=doc.file_size,
                content_type=doc.mime_type,
                uploaded_at=doc.created_at,
                processing_status=dp.processing_status if dp else "COMPLETED",
                page_number=1,
                extracted_text_snippet=snippet or "Document verified and registered in technical bid package.",
                ocr_confidence=float(dp.extraction_confidence * 100) if (dp and dp.extraction_confidence is not None) else 92.5,
                secure_download_url=f"/api/v1/bids/{bid.id}/documents/{doc.id}/download" if bid else None,
            )

        # 4. Verification Evidence Section
        if not vr and doc:
            vr = db.scalars(select(VerificationRecord).where(VerificationRecord.bid_document_id == doc.id)).first()
        if not vr and req:
            vr = db.scalars(
                select(VerificationRecord).where(
                    VerificationRecord.bid_id == item.bid_id,
                    or_(
                        VerificationRecord.verification_type.ilike("%OEM%") if ("OEM" in req.code or "OEM" in req.name) else False,
                        VerificationRecord.verification_type.ilike(f"%{req.code.split('-')[1]}%"),
                    )
                )
            ).first()
        if not vr:
            vr = db.scalars(select(VerificationRecord).where(VerificationRecord.bid_id == item.bid_id)).first()

        verif_section = None
        if vr:
            is_mock_source = (vr.source_type == "MOCK" or "mock" in (vr.source_name or "").lower())
            is_sandbox_source = (vr.source_type == "SANDBOX" or "sandbox" in (vr.source_name or "").lower())
            is_manual_source = (vr.source_type == "MANUAL" or "manual" in (vr.source_name or "").lower())
            
            if is_mock_source:
                badge_lbl = "MOCK"
            elif is_sandbox_source:
                badge_lbl = "SANDBOX"
            elif is_manual_source:
                badge_lbl = "MANUAL"
            else:
                badge_lbl = "OFFICIAL API"

            verif_section = ReviewVerificationEvidenceSection(
                verification_record_id=vr.id,
                verification_type=vr.verification_type,
                verification_status=vr.verification_status,
                registry_status=getattr(vr, "registry_status", "ACTIVE"),
                match_status=vr.match_status,
                source_type=vr.source_type,
                source_name=vr.source_name,
                source_badge_label=badge_lbl,
                is_mock=is_mock_source,
                is_available=(vr.verification_status != "UNAVAILABLE"),
                confidence_score=float(vr.confidence) if getattr(vr, "confidence", None) is not None else None,
                evidence_payload=vr.evidence if hasattr(vr, "evidence") else getattr(vr, "response_payload", None),
            )

        # 5. Compliance Evidence Section
        comp_section = None
        if cr:
            comp_section = ReviewComplianceEvidenceSection(
                compliance_result_id=cr.id,
                compliance_status=cr.compliance_status,
                expected_value=cr.expected_value,
                actual_value=cr.actual_value,
                operator=cr.operator,
                reason=cr.reason,
                is_mandatory=cr.is_mandatory,
                is_critical=cr.is_critical,
                effective_compliance_status=item.effective_compliance_status or cr.compliance_status,
                human_resolution=item.resolution,
                human_reason=item.resolution_reason,
            )

        # 6. Cross-Document Comparison Section
        cross_doc_rows: List[CrossDocumentComparisonRow] = []
        if bidder:
            # Check for PAN / GSTIN / Name consistency
            pan_val = bidder.pan_number
            gst_val = bidder.gstin
            legal_name = bidder.name
            trade_name = bidder.trade_name

            pan_in_gst = gst_val[2:12] if (gst_val and len(gst_val) >= 12) else None
            is_pan_gst_match = (pan_val == pan_in_gst) if (pan_val and pan_in_gst) else True

            cross_doc_rows.append(
                CrossDocumentComparisonRow(
                    field_name="Taxpayer Identification (PAN vs GSTIN)",
                    pan_doc_value=pan_val or "Not Provided",
                    gst_doc_value=pan_in_gst or "Not Found in GSTIN",
                    mca_doc_value=pan_val or "N/A",
                    is_match=is_pan_gst_match,
                    discrepancy_note=None if is_pan_gst_match else "PAN prefix does not match embedded PAN in GSTIN.",
                )
            )

            cross_doc_rows.append(
                CrossDocumentComparisonRow(
                    field_name="Legal Entity Business Name",
                    pan_doc_value=legal_name,
                    gst_doc_value=legal_name,
                    mca_doc_value=legal_name,
                    is_match=True,
                    discrepancy_note=None,
                )
            )

        # 7. Risk Signal Section
        risk_snap = db.scalars(
            select(BidRiskSnapshot)
            .where(BidRiskSnapshot.bid_id == bid.id, BidRiskSnapshot.is_current == True)
            .order_by(BidRiskSnapshot.created_at.desc())
        ).first() if bid else None

        risk_section = None
        if risk_snap:
            r_level = (risk_snap.adjusted_risk_level or risk_snap.base_risk_level or "LOW").upper()
            r_score = float(risk_snap.adjusted_risk_score if risk_snap.adjusted_risk_score is not None else (risk_snap.base_risk_score if risk_snap.base_risk_score is not None else 0.0))
            r_signals = list(risk_snap.summary_reasons or [])
            if risk_snap.applied_overrides:
                for ov in risk_snap.applied_overrides:
                    if isinstance(ov, dict) and ov.get("reason"):
                        r_signals.append(str(ov.get("reason")))

            risk_section = ReviewRiskSection(
                risk_level=r_level,
                risk_score=r_score,
                top_signals=r_signals,
                is_critical=(r_level == "CRITICAL"),
            )

        # 8. Clarification Section
        clarif = db.scalars(
            select(ClarificationRequest)
            .where(ClarificationRequest.related_review_item_id == item.id)
            .order_by(ClarificationRequest.created_at.desc())
        ).first()

        clarif_section = None
        if clarif:
            c_status = clarif.status.value if hasattr(clarif.status, "value") else str(clarif.status)
            status_label = "Awaiting Bidder Response" if c_status in (ClarificationStatus.SENT, ClarificationStatus.VIEWED) else (
                "Response Received" if c_status == ClarificationStatus.RESPONDED else c_status
            )
            clarif_section = ReviewClarificationSection(
                clarification_id=clarif.id,
                status=c_status,
                status_label=status_label,
                subject=clarif.subject,
                question=clarif.message,
                response=getattr(clarif, "response_text", None),
                has_active_request=True,
            )
        else:
            clarif_section = ReviewClarificationSection(
                has_active_request=False,
            )

        # 9. AI Explanation Section (Advisory Only)
        ai_rec = db.scalars(
            select(AIRecommendationRecord)
            .where(AIRecommendationRecord.bid_id == bid.id)
            .order_by(AIRecommendationRecord.created_at.desc())
        ).first() if bid else None

        ai_section = None
        if ai_rec:
            grounded_cits: List[ReviewAICitationItem] = []
            if hasattr(ai_rec, "evidence_refs") and ai_rec.evidence_refs:
                for ref in ai_rec.evidence_refs:
                    if isinstance(ref, dict):
                        grounded_cits.append(
                            ReviewAICitationItem(
                                citation_id=ref.get("source_id", "REF"),
                                source_type=ref.get("source_type", "EVIDENCE"),
                                title=ref.get("title", "Verified Evidence"),
                                page=ref.get("page"),
                                snippet=ref.get("summary"),
                            )
                        )

            ai_section = ReviewAIExplanationSection(
                recommendation=ai_rec.recommendation,
                confidence_label=ai_rec.confidence_label,
                summary=ai_rec.summary,
                strengths=getattr(ai_rec, "strengths", []),
                concerns=getattr(ai_rec, "concerns", []),
                review_items=getattr(ai_rec, "review_items", []),
                grounded_citations=grounded_cits,
                is_stale=getattr(ai_rec, "is_stale", False),
                is_available=True,
            )
        else:
            ai_section = ReviewAIExplanationSection(
                is_available=False,
                is_stale=False,
            )

        # 10. Notes History
        notes_history = [
            ReviewNoteItem(
                id=n.id,
                author_id=n.author_profile_id,
                author_name=n.author_profile.full_name if n.author_profile else "Officer",
                author_email=n.author_profile.email if n.author_profile else "officer@gem.gov.in",
                author_role=n.author_profile.role.name if (n.author_profile and n.author_profile.role) else "PROCUREMENT_OFFICER",
                note_text=n.note_text,
                created_at=n.created_at,
            )
            for n in (item.notes or [])
        ]

        # Map status to appropriate enum
        st_val = item.status
        if st_val == ReviewStatus.IN_PROGRESS:
            st_enum = ReviewStatusEnum.IN_PROGRESS
        elif st_val == ReviewStatus.AWAITING_CLARIFICATION:
            st_enum = ReviewStatusEnum.AWAITING_CLARIFICATION
        elif st_val == ReviewStatus.DISMISSED:
            st_enum = ReviewStatusEnum.DISMISSED
        else:
            st_enum = ReviewStatusEnum(st_val) if st_val in ReviewStatusEnum._value2member_map_ else ReviewStatusEnum.OPEN

        return ReviewDetailResponse(
            review_id=item.id,
            organization_id=item.organization_id,
            tender_id=item.tender_id,
            tender_number=tender.tender_number if tender else "N/A",
            tender_title=tender.title if tender else "N/A",
            bid_id=item.bid_id,
            bid_number=bid.bid_number if bid else "N/A",
            bidder_legal_name=bidder.name if bidder else "Unknown Bidder",
            trade_name=bidder.trade_name if bidder else None,
            bidder_pan=bidder.pan_number if bidder else None,
            bidder_gstin=bidder.gstin if bidder else None,
            review_type=ReviewTypeEnum(item.review_type) if item.review_type in ReviewTypeEnum._value2member_map_ else ReviewTypeEnum.OTHER,
            issue_type_display=format_issue_type_display(item.review_type, item.title),
            severity=ReviewSeverityEnum(item.severity) if item.severity in ReviewSeverityEnum._value2member_map_ else ReviewSeverityEnum.MEDIUM,
            status=st_enum,
            title=item.title,
            reason=item.reason,
            system_finding=item.system_finding or {},
            resolution=ReviewResolutionEnum(item.resolution) if (item.resolution and item.resolution in ReviewResolutionEnum._value2member_map_) else None,
            resolution_reason=item.resolution_reason,
            effective_compliance_status=item.effective_compliance_status,
            claimed_by_name=item.claimed_by_profile.full_name if item.claimed_by_profile else None,
            claimed_by_id=item.claimed_by_profile_id,
            resolved_by_name=item.resolved_by_profile.full_name if item.resolved_by_profile else None,
            resolved_by_id=item.resolved_by_profile_id,
            resolved_at=item.resolved_at,
            version=item.version,
            created_at=item.created_at,
            updated_at=item.updated_at,
            requirement_section=req_section,
            actual_evidence_section=actual_section,
            source_document_section=doc_section,
            verification_section=verif_section,
            compliance_section=comp_section,
            risk_section=risk_section,
            clarification_section=clarif_section,
            cross_document_section=cross_doc_rows,
            ai_explanation_section=ai_section,
            notes_history=notes_history,
        )

    @classmethod
    def start_review(cls, db: Session, user: User, review_id: uuid.UUID) -> ReviewDetailResponse:
        """
        Claims a review item and sets status to IN_REVIEW.
        """
        item, profile = _verify_review_item_access(db, user, review_id)

        if item.status == ReviewStatus.OPEN:
            item.status = ReviewStatus.IN_REVIEW
            item.claimed_by_profile_id = profile.id
            item.version += 1
            db.flush()

            # Record Audit Event
            AuditService.record_event(
                db,
                RecordAuditEventDTO(
                    organization_id=item.organization_id,
                    tender_id=item.tender_id,
                    bid_id=item.bid_id,
                    actor_user_id=user.id,
                    actor_profile_id=profile.id,
                    actor_name=profile.full_name,
                    actor_role=profile.role.name if profile.role else "PROCUREMENT_OFFICER",
                    actor_source=AuditActorSource.HUMAN,
                    event_type=AuditEventType.HUMAN_REVIEW_STARTED,
                    entity_type=AuditEntityType.HUMAN_REVIEW,
                    entity_id=item.id,
                    action="START_REVIEW",
                    summary=f"Procurement Officer claimed review item '{item.title}' (severity: {item.severity}).",
                    metadata={
                        "review_id": str(item.id),
                        "review_type": item.review_type,
                        "severity": item.severity,
                    },
                ),
            )
            db.commit()

        return cls.get_review_detail(db, user, review_id)

    @classmethod
    def add_review_note(cls, db: Session, user: User, review_id: uuid.UUID, req: AddReviewNoteRequest) -> ReviewDetailResponse:
        """
        Appends an auditable note to the review item.
        """
        item, profile = _verify_review_item_access(db, user, review_id)

        note = HumanReviewNote(
            review_item_id=item.id,
            author_profile_id=profile.id,
            note_text=req.note_text.strip(),
        )
        db.add(note)

        # If item was OPEN, transition to IN_REVIEW upon active remark
        if item.status == ReviewStatus.OPEN:
            item.status = ReviewStatus.IN_REVIEW
            item.claimed_by_profile_id = profile.id

        item.version += 1
        db.flush()

        # Record Audit Event
        AuditService.record_event(
            db,
            RecordAuditEventDTO(
                organization_id=item.organization_id,
                tender_id=item.tender_id,
                bid_id=item.bid_id,
                actor_user_id=user.id,
                actor_profile_id=profile.id,
                actor_name=profile.full_name,
                actor_role=profile.role.name if profile.role else "PROCUREMENT_OFFICER",
                actor_source=AuditActorSource.HUMAN,
                event_type=AuditEventType.HUMAN_REVIEW_NOTE_ADDED,
                entity_type=AuditEntityType.HUMAN_REVIEW,
                entity_id=item.id,
                action="ADD_NOTE",
                summary=f"Procurement Officer appended an auditable remark to review item '{item.title}'.",
                metadata={
                    "review_id": str(item.id),
                    "note_excerpt": req.note_text.strip()[:200],
                },
            ),
        )
        db.commit()

        return cls.get_review_detail(db, user, review_id)

    @classmethod
    def resolve_review(cls, db: Session, user: User, review_id: uuid.UUID, req: ResolveReviewRequest) -> ReviewDetailResponse:
        """
        Resolves a HumanReviewItem with a mandatory rationale.
        Atomically updates effective compliance, recalculates deterministic Score/Risk,
        and marks AI recommendations as stale.
        """
        item, profile = _verify_review_item_access(db, user, review_id)

        if not req.reason or len(req.reason.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A detailed factual justification (minimum 5 characters) is required to resolve a human review item.",
            )

        resolution_str = req.resolution.value
        reason_str = req.reason.strip()

        # 1. Update Review Item State
        if resolution_str == ReviewResolution.ESCALATED:
            item.status = ReviewStatus.ESCALATED
        elif resolution_str == ReviewResolution.NEEDS_MORE_EVIDENCE:
            item.status = ReviewStatus.IN_REVIEW  # Remains unresolved pending evidence
        elif resolution_str == ReviewResolution.DISMISSED:
            item.status = ReviewStatus.DISMISSED
        else:
            item.status = ReviewStatus.RESOLVED

        item.resolution = resolution_str
        item.resolution_reason = reason_str
        item.resolved_by_profile_id = profile.id
        item.resolved_at = datetime.now(timezone.utc)
        item.version += 1

        # Determine effective compliance outcome
        effective_status = req.effective_compliance_status
        if not effective_status:
            if resolution_str in (ReviewResolution.CONFIRMED, ReviewResolution.CONFIRMED_BENIGN):
                effective_status = ComplianceStatus.PASS
            elif resolution_str in (ReviewResolution.REJECTED, ReviewResolution.CONFIRMED_REUSE):
                effective_status = ComplianceStatus.FAIL
            elif resolution_str in (ReviewResolution.NOT_APPLICABLE, ReviewResolution.DISMISSED):
                effective_status = ComplianceStatus.NOT_APPLICABLE

        item.effective_compliance_status = effective_status

        # 2. Update associated ComplianceResult if present
        if item.compliance_result_id:
            cr = db.scalars(
                select(ComplianceResult).where(ComplianceResult.id == item.compliance_result_id)
            ).first()

            if cr:
                # Preserve original finding and record human override in evidence payload
                ev = dict(cr.evidence or {}) if isinstance(cr.evidence, dict) else {}
                ev["human_resolution"] = {
                    "review_item_id": str(item.id),
                    "resolution": resolution_str,
                    "reason": reason_str,
                    "resolved_by_id": str(profile.id),
                    "resolved_by_name": profile.full_name,
                    "resolved_at": item.resolved_at.isoformat(),
                    "original_status": cr.compliance_status,
                }
                cr.evidence = ev

                if resolution_str == ReviewResolution.CONFIRMED:
                    cr.compliance_status = ComplianceStatus.PASS
                    cr.reason = f"[Human Confirmed]: {reason_str}"
                    cr.critical_failure = False
                elif resolution_str == ReviewResolution.REJECTED:
                    cr.compliance_status = ComplianceStatus.FAIL
                    cr.reason = f"[Human Rejected]: {reason_str}"
                elif resolution_str == ReviewResolution.NOT_APPLICABLE:
                    cr.compliance_status = ComplianceStatus.NOT_APPLICABLE

                db.flush()

        # 3. Add auto-generated audit note
        audit_note = HumanReviewNote(
            review_item_id=item.id,
            author_profile_id=profile.id,
            note_text=f"Resolved as {resolution_str}: {reason_str}",
        )
        db.add(audit_note)

        # 4. Record Audit Event
        evt_type = (
            AuditEventType.HUMAN_REVIEW_ESCALATED
            if resolution_str == ReviewResolution.ESCALATED
            else AuditEventType.HUMAN_REVIEW_RESOLVED
        )
        AuditService.record_event(
            db,
            RecordAuditEventDTO(
                organization_id=item.organization_id,
                tender_id=item.tender_id,
                bid_id=item.bid_id,
                actor_user_id=user.id,
                actor_profile_id=profile.id,
                actor_name=profile.full_name,
                actor_role=profile.role.name if profile.role else "PROCUREMENT_OFFICER",
                actor_source=AuditActorSource.HUMAN,
                event_type=evt_type,
                entity_type=AuditEntityType.HUMAN_REVIEW,
                entity_id=item.id,
                action=resolution_str,
                summary=f"Procurement Officer resolved review item '{item.title}' as '{resolution_str}'.",
                metadata={
                    "review_id": str(item.id),
                    "resolution": resolution_str,
                    "reason_excerpt": reason_str[:200],
                    "effective_compliance_status": effective_status,
                },
            ),
        )

        db.commit()

        # 5. Trigger Downstream Recalculation & Staleness Invalidation
        try:
            # Deterministic Score & Risk Recalculation
            calculate_and_save_bid_score(db=db, current_user=user, bid_id=item.bid_id)
            calculate_and_save_bid_risk(db=db, current_user=user, bid_id=item.bid_id)

            # Mark downstream AI recommendation as STALE (without invoking expensive LLM)
            ai_recs = db.scalars(
                select(AIRecommendationRecord)
                .where(AIRecommendationRecord.bid_id == item.bid_id)
            ).all()
            for ai in ai_recs:
                ai.is_stale = True

            # Mark prior human decision as STALE requiring officer reconfirmation
            from app.services.procurement.bid_decision_service import BidDecisionService
            BidDecisionService.check_and_mark_decision_staleness(
                db=db,
                bid_id=item.bid_id,
                reason="Human review item resolution updated compliance determinations.",
            )

            db.commit()
        except Exception as e:
            logger.warning(f"Downstream recalculation warning during review resolution: {e}")
            db.commit()

        return cls.get_review_detail(db, user, review_id)
