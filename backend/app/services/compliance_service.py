"""
Compliance Evaluation Service for Part 6A
Orchestrates compliance evaluation lifecycle, RBAC & multi-tenant security,
database persistence, versioning, and summary aggregation.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select, and_, func, or_
from sqlalchemy.orm import Session, selectinload, joinedload

from app.compliance.engine import build_compliance_context, evaluate_requirement
from app.compliance.types import ComplianceStatus
from app.db.models.bid import Bid
from app.db.models.compliance_result import ComplianceResult
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.bid_document import BidDocument
from app.db.models.document_processing import DocumentProcessing
from app.db.models.user import User
from app.schemas.compliance import (
    BidComplianceSummaryResponse,
    ComplianceResultItemResponse,
    ComplianceSummaryCounts,
)


def _get_bid_for_compliance_access(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
) -> Tuple[Profile, Bid, Tender]:
    """
    Validates tenant ownership and role-based access for compliance operations.
    - BIDDER: must belong to the bidding organization.
    - PROCUREMENT_OFFICER: must belong to the organization owning the tender.
    - ADMIN: unrestricted access across all organizations.
    Raises HTTP 404 on unauthorized access or missing records.
    """
    profile = db.scalars(
        select(Profile).where(Profile.id == current_user.profile_id)
    ).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found.",
        )

    bid = db.scalars(
        select(Bid)
        .options(
            selectinload(Bid.documents).selectinload(BidDocument.processing),
            selectinload(Bid.bidder_organization),
        )
        .where(
            and_(
                Bid.id == bid_id,
                Bid.is_active == True,
            )
        )
    ).first()
    if not bid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bid submission record not found.",
        )

    tender = db.scalars(
        select(Tender).where(
            and_(
                Tender.id == bid.tender_id,
                Tender.is_active == True,
            )
        )
    ).first()
    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated tender not found.",
        )

    role = db.scalars(select(Role).where(Role.id == profile.role_id)).first()
    role_name = role.name if role else ""

    if role_name == "BIDDER":
        if bid.bidder_organization_id != profile.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bid submission record not found.",
            )
    elif role_name == "PROCUREMENT_OFFICER":
        if tender.organization_id != profile.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bid submission record not found.",
            )
    elif role_name == "ADMIN":
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized role for compliance evaluation.",
        )

    return profile, bid, tender


def evaluate_bid_compliance(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
) -> BidComplianceSummaryResponse:
    """
    Executes compliance evaluation for all active TenderRequirements of the bid's tender.
    - Preserves audit history by superseding previous evaluation records.
    - Idempotently creates current compliance results.
    - Links verified evidence and justification reasons.
    """
    profile, bid, tender = _get_bid_for_compliance_access(db, current_user, bid_id)

    # 1. Load active tender requirements
    requirements = db.scalars(
        select(TenderRequirement)
        .where(
            and_(
                TenderRequirement.tender_id == tender.id,
                TenderRequirement.is_active == True,
            )
        )
        .order_by(TenderRequirement.display_order.asc(), TenderRequirement.created_at.asc())
    ).all()

    if not requirements:
        return BidComplianceSummaryResponse(
            bid_id=bid.id,
            tender_id=tender.id,
            tender_number=tender.tender_number,
            bidder_name=bid.bidder_organization.name if bid.bidder_organization else None,
            compliance_evaluation_complete=True,
            counts=ComplianceSummaryCounts(),
            results=[],
            evaluated_at=datetime.now(timezone.utc),
        )

    # 2. Build evaluation context
    context = build_compliance_context(db, bid.id)

    # 3. Determine next evaluation version
    max_ver = db.scalar(
        select(func.max(ComplianceResult.evaluation_version)).where(
            ComplianceResult.bid_id == bid.id
        )
    )
    next_version = (max_ver or 0) + 1
    eval_now = datetime.now(timezone.utc)

    # 4. Supersede current results
    existing_current = db.scalars(
        select(ComplianceResult).where(
            and_(
                ComplianceResult.bid_id == bid.id,
                ComplianceResult.is_current == True,
            )
        )
    ).all()
    for prev in existing_current:
        prev.is_current = False

    # 5. Evaluate each requirement and persist new results
    from app.db.models.tender_requirement_version import TenderRequirementVersion

    created_results: List[ComplianceResult] = []
    for req in requirements:
        rule_res = evaluate_requirement(req, context)
        is_crit = getattr(req, "is_critical", False) or rule_res.is_critical
        is_crit_fail = is_crit and (rule_res.compliance_status == ComplianceStatus.FAIL)

        ev_data = dict(rule_res.evidence) if isinstance(rule_res.evidence, dict) else {}
        if rule_res.review_type and "review_type" not in ev_data:
            ev_data["review_type"] = rule_res.review_type

        # Resolve active rule version
        rule_ver = db.scalars(
            select(TenderRequirementVersion).where(
                TenderRequirementVersion.tender_requirement_id == req.id
            ).order_by(TenderRequirementVersion.version_number.desc())
        ).first()

        rule_ver_id = rule_ver.id if rule_ver else None
        rule_ver_num = rule_ver.version_number if rule_ver else getattr(req, "current_version_number", 1)

        comp_rec = ComplianceResult(
            id=uuid.uuid4(),
            bid_id=bid.id,
            tender_id=tender.id,
            tender_requirement_id=req.id,
            rule_version_id=rule_ver_id,
            rule_version_number=rule_ver_num,
            compliance_status=rule_res.compliance_status,
            actual_value=rule_res.actual_value,
            expected_value=rule_res.expected_value,
            operator=rule_res.operator,
            reason=rule_res.reason,
            evidence=ev_data,
            source_verification_ids=rule_res.source_verification_ids,
            is_mandatory=rule_res.is_mandatory,
            is_critical=is_crit,
            critical_failure=is_crit_fail,
            weight=rule_res.weight,
            evaluation_version=next_version,
            is_current=True,
            evaluated_at=eval_now,
        )
        db.add(comp_rec)
        created_results.append(comp_rec)

    db.commit()

    # 6. Build response
    return _build_compliance_summary_response(bid, tender, created_results, eval_now)


def get_bid_compliance(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
) -> BidComplianceSummaryResponse:
    """
    Retrieves the current compliance evaluation results for a bid.
    """
    profile, bid, tender = _get_bid_for_compliance_access(db, current_user, bid_id)

    current_results = db.scalars(
        select(ComplianceResult)
        .options(selectinload(ComplianceResult.tender_requirement))
        .where(
            and_(
                ComplianceResult.bid_id == bid.id,
                ComplianceResult.is_current == True,
            )
        )
    ).all()

    evaluated_at = current_results[0].evaluated_at if current_results else None
    return _build_compliance_summary_response(bid, tender, list(current_results), evaluated_at)


def _extract_evidence_fields_for_rule(
    r: ComplianceResult,
    bid: Bid,
) -> Tuple[Optional[uuid.UUID], Optional[str], Optional[int], Optional[str], Optional[str], Optional[float], Optional[str]]:
    """
    Extracts direct evidence fields:
    (document_id, document_name, page_number, download_url, evidence_snippet, confidence, verification_source)
    """
    ev_dict = r.evidence if isinstance(r.evidence, dict) else {}
    doc_id: Optional[uuid.UUID] = None
    doc_name: Optional[str] = ev_dict.get("document_name") or ev_dict.get("original_filename")
    page_num: Optional[int] = ev_dict.get("page_number") or ev_dict.get("page") or ev_dict.get("source_page")
    snippet: Optional[str] = (
        ev_dict.get("evidence_snippet")
        or ev_dict.get("snippet")
        or ev_dict.get("source_text")
        or ev_dict.get("matched_text")
    )
    confidence: Optional[float] = ev_dict.get("confidence") or ev_dict.get("extraction_confidence")
    verif_source: Optional[str] = (
        ev_dict.get("source_name")
        or ev_dict.get("source")
        or ev_dict.get("verification_source")
        or ev_dict.get("authority")
    )

    # Parse document_id if in evidence
    if ev_dict.get("document_id"):
        try:
            doc_id = uuid.UUID(str(ev_dict["document_id"]))
        except Exception:
            pass

    req = r.tender_requirement
    req_code = (req.code if req else "").upper()
    req_name = (req.name if req else "").upper()
    req_cat = (req.category if req else "").upper()

    matching_doc = None
    if hasattr(bid, "documents") and bid.documents:
        active_docs = [d for d in bid.documents if getattr(d, "is_active", True)]
        if doc_id:
            matching_doc = next((d for d in active_docs if str(getattr(d, "id", "")) == str(doc_id)), None)
        if not matching_doc and (req or getattr(r, "tender_requirement_id", None)):
            target_req_id = req.id if req else getattr(r, "tender_requirement_id", None)
            matching_doc = next((d for d in active_docs if getattr(d, "tender_requirement_id", None) == target_req_id), None)
        if not matching_doc and req_code:
            matching_doc = next((d for d in active_docs if getattr(d, "document_type", None) and getattr(d, "document_type", "").upper() in req_code), None)
        if not matching_doc and req_cat:
            matching_doc = next((d for d in active_docs if d.document_type and d.document_type.upper() in req_cat), None)
        if not matching_doc and ("TURNOVER" in req_code or "FINANCIAL" in req_code or "FINANCIAL" in req_cat or "PROFIT" in req_code):
            matching_doc = next((d for d in active_docs if d.document_type in ("FINANCIAL_STATEMENT", "TURNOVER_CERTIFICATE")), None)
        if not matching_doc and ("GST" in req_code or "GST" in req_name):
            matching_doc = next((d for d in active_docs if d.document_type == "GST_CERTIFICATE"), None)
        if not matching_doc and ("PAN" in req_code or "PAN" in req_name):
            matching_doc = next((d for d in active_docs if d.document_type == "PAN"), None)
        if not matching_doc and ("UDYAM" in req_code or "MSME" in req_code):
            matching_doc = next((d for d in active_docs if d.document_type == "UDYAM_CERTIFICATE"), None)
        if not matching_doc and ("OEM" in req_code or "MAF" in req_code):
            matching_doc = next((d for d in active_docs if d.document_type == "OEM_AUTHORIZATION"), None)
        if not matching_doc and ("LOCAL_CONTENT" in req_code or "MII" in req_code):
            matching_doc = next((d for d in active_docs if d.document_type == "LOCAL_CONTENT_DECLARATION"), None)
        if not matching_doc and ("BIS" in req_code or "CRS" in req_code):
            matching_doc = next((d for d in active_docs if d.document_type in ("TECHNICAL_DOCUMENT", "OTHER")), None)
        if not matching_doc and ("EXPERIENCE" in req_code or "PROJECT" in req_code):
            matching_doc = next((d for d in active_docs if d.document_type == "EXPERIENCE_CERTIFICATE"), None)

    if matching_doc:
        doc_id = matching_doc.id
        if not doc_name:
            doc_name = matching_doc.original_filename or matching_doc.document_name

        dp = getattr(matching_doc, "processing", None)
        if dp:
            if confidence is None and dp.extraction_confidence is not None:
                confidence = float(dp.extraction_confidence)
            if dp.extracted_data and isinstance(dp.extracted_data, dict):
                fields = dp.extracted_data.get("fields", {})
                if isinstance(fields, dict):
                    for fk, fval in fields.items():
                        if isinstance(fval, dict):
                            if page_num is None and fval.get("page"):
                                try:
                                    page_num = int(fval["page"])
                                except Exception:
                                    pass
                            if not snippet and fval.get("evidence"):
                                snippet = str(fval["evidence"])
                            if confidence is None and fval.get("confidence") is not None:
                                confidence = float(fval["confidence"])
                            if not verif_source and fval.get("source"):
                                verif_source = str(fval["source"])
            if not snippet:
                txt = dp.raw_text or dp.normalized_text
                if txt:
                    snippet = txt[:250].strip() + ("..." if len(txt) > 250 else "")

    if not page_num and doc_id:
        page_num = 1

    download_url = f"/api/v1/procurement/bids/{bid.id}/documents/{doc_id}/download" if doc_id else None

    return doc_id, doc_name, page_num, download_url, snippet, confidence, verif_source


def _build_compliance_summary_response(
    bid: Bid,
    tender: Tender,
    results: List[ComplianceResult],
    evaluated_at: Optional[datetime],
) -> BidComplianceSummaryResponse:
    """
    Synthesizes evaluated compliance rows into a unified response summary.
    """
    counts = ComplianceSummaryCounts(total=len(results))
    item_responses: List[ComplianceResultItemResponse] = []
    review_items = []

    for r in results:
        status_val = r.compliance_status
        if status_val == ComplianceStatus.PASS:
            counts.passed += 1
        elif status_val == ComplianceStatus.FAIL:
            counts.failed += 1
            if r.is_mandatory:
                counts.mandatory_failures += 1
            if r.is_critical or r.critical_failure:
                counts.critical_failures += 1
        elif status_val == ComplianceStatus.REVIEW:
            counts.review += 1
        elif status_val == ComplianceStatus.PENDING:
            counts.pending += 1
        elif status_val == ComplianceStatus.NOT_APPLICABLE:
            counts.not_applicable += 1
        elif status_val == ComplianceStatus.BLOCKED:
            counts.blocked += 1

        req = r.tender_requirement
        req_code = req.code if req else "UNKNOWN"
        req_name = req.name if req else "Unknown Requirement"
        category = req.category if req else "GENERAL"
        req_type = req.requirement_type if req else "TEXT"

        is_crit = r.is_critical if hasattr(r, "is_critical") else False
        is_crit_fail = r.critical_failure if hasattr(r, "critical_failure") else (is_crit and status_val == ComplianceStatus.FAIL)

        (
            doc_id,
            doc_name,
            page_num,
            download_url,
            snippet,
            confidence_val,
            verif_source,
        ) = _extract_evidence_fields_for_rule(r, bid)

        item_responses.append(
            ComplianceResultItemResponse(
                id=r.id,
                bid_id=r.bid_id,
                tender_id=r.tender_id,
                tender_requirement_id=r.tender_requirement_id,
                requirement_code=req_code,
                requirement_name=req_name,
                category=category,
                requirement_type=req_type,
                compliance_status=r.compliance_status,
                actual_value=r.actual_value,
                expected_value=r.expected_value,
                operator=r.operator,
                reason=r.reason,
                evidence=r.evidence,
                source_verification_ids=r.source_verification_ids,
                document_id=doc_id,
                document_name=doc_name,
                page_number=page_num,
                download_url=download_url,
                evidence_snippet=snippet,
                confidence=confidence_val,
                verification_source=verif_source,
                is_mandatory=r.is_mandatory,
                is_critical=is_crit,
                critical_failure=is_crit_fail,
                weight=r.weight,
                rule_version_id=getattr(r, "rule_version_id", None),
                rule_version_number=getattr(r, "rule_version_number", 1),
                evaluation_version=r.evaluation_version,
                is_current=r.is_current,
                evaluated_at=r.evaluated_at,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )

        # Collect review item if status is REVIEW
        if status_val == ComplianceStatus.REVIEW:
            ev_dict = r.evidence if isinstance(r.evidence, dict) else {}
            review_type = ev_dict.get("review_type") or "HUMAN_REVIEW_REQUIRED"
            source_name = ev_dict.get("source_name") or ev_dict.get("source")

            from app.schemas.compliance import ComplianceReviewItemResponse
            review_items.append(
                ComplianceReviewItemResponse(
                    requirement_id=r.tender_requirement_id,
                    requirement_code=req_code,
                    requirement_name=req_name,
                    category=category,
                    compliance_status=r.compliance_status,
                    review_type=review_type,
                    reason=r.reason,
                    evidence=r.evidence,
                    source_name=source_name,
                    is_mandatory=r.is_mandatory,
                    is_critical=is_crit,
                )
            )

    # Evaluation is complete when all items are in terminal statuses (none PENDING or BLOCKED)
    is_complete = len(results) > 0 and all(
        r.compliance_status in ComplianceStatus.TERMINAL for r in results
    )

    bidder_name = bid.bidder_organization.name if bid.bidder_organization else None

    return BidComplianceSummaryResponse(
        bid_id=bid.id,
        tender_id=tender.id,
        tender_number=tender.tender_number,
        bidder_name=bidder_name,
        compliance_evaluation_complete=is_complete,
        counts=counts,
        results=item_responses,
        review_items=review_items,
        evaluated_at=evaluated_at,
    )
