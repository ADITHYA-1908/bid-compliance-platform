"""
Verification Service for Part 5A
Provides business logic, multi-tenant security, idempotency control,
retry orchestration, and state lifecycle management for claim verifications.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.document_processing import (
    DocumentClass,
    DocumentProcessing,
    ProcessingStage,
    ProcessingStatus,
)
from app.db.models.profile import Profile
from app.db.models.user import User
from app.db.models.verification_record import VerificationRecord
from app.schemas.verification import (
    BidVerificationListResponse,
    DocumentVerificationListResponse,
    VerificationRecordResponse,
    VerificationRetryResponse,
    VerificationSummaryItem,
    VerificationTriggerResponse,
)
from app.services.bid_document_service import _get_bid_for_bidder
from app.services.verification_engine import verification_engine
from app.verification.adapters.base import VerificationRequest, VerificationResult
from app.verification.types import (
    VerificationClaimSource,
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationTriggerSource,
    VerificationType,
)

logger = logging.getLogger(__name__)


def _get_document_for_verification(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
) -> Tuple[Profile, Bid, BidDocument]:
    """
    Validates tenant ownership and retrieves the BidDocument with linked processing records.
    Allows verification queries and execution on both DRAFT and SUBMITTED bids.
    Returns HTTP 404 if bid or document does not belong to the authenticated bidder.
    """
    profile, bid = _get_bid_for_bidder(db, current_user, bid_id)

    doc = db.scalars(
        select(BidDocument)
        .options(
            joinedload(BidDocument.processing),
            joinedload(BidDocument.tender_requirement),
        )
        .where(
            BidDocument.id == document_id,
            BidDocument.bid_id == bid.id,
        )
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or does not belong to this bid.",
        )

    return profile, bid, doc


def discover_claims_for_document(
    doc: BidDocument,
    proc: Optional[DocumentProcessing],
) -> List[Tuple[str, str, str, Dict[str, Any]]]:
    """
    Inspects structured extracted entities and document classification to identify
    verifiable statutory and compliance claims.
    Returns list of tuples: (VerificationType, primary_claimed_value, field_key, supporting_claims_dict).
    """
    claims: List[Tuple[str, str, str, Dict[str, Any]]] = []

    if not proc or not proc.extracted_data:
        return claims

    fields_dict: Dict[str, Any] = proc.extracted_data.get("fields", {})

    def _get_val(k: str) -> Optional[str]:
        item = fields_dict.get(k)
        if isinstance(item, dict) and item.get("value") is not None:
            return str(item["value"]).strip()
        elif isinstance(item, str):
            return item.strip()
        return None

    # 1. GSTIN Claim Discovery
    gstin_val = _get_val("gstin") or _get_val("gst_number")
    if gstin_val:
        supp_gst = {
            "legal_name": _get_val("legal_name") or _get_val("company_name"),
            "trade_name": _get_val("trade_name"),
            "state": _get_val("state"),
            "registration_date": _get_val("registration_date"),
            "address": _get_val("address"),
        }
        claims.append((VerificationType.GST, gstin_val, "gstin", supp_gst))

    # 2. PAN Number Claim Discovery
    pan_val = _get_val("pan_number") or _get_val("pan")
    if pan_val:
        supp_pan = {
            "name": _get_val("holder_name") or _get_val("name") or _get_val("legal_name") or _get_val("entity_name"),
            "holder_name": _get_val("holder_name"),
            "father_name": _get_val("father_name"),
            "date_of_birth_or_incorporation": _get_val("date_of_birth_or_incorporation") or _get_val("dob"),
        }
        claims.append((VerificationType.PAN, pan_val, "pan_number", supp_pan))

    # 3. Udyam Registration Number Claim Discovery
    udyam_val = (
        _get_val("udyam_registration_number")
        or _get_val("udyam_number")
        or _get_val("msme_registration_number")
    )
    if udyam_val:
        supp_udyam = {
            "enterprise_name": _get_val("enterprise_name") or _get_val("legal_name") or _get_val("company_name"),
            "organization_type": _get_val("organization_type"),
            "enterprise_type": _get_val("enterprise_type") or _get_val("enterprise_classification"),
            "enterprise_classification": _get_val("enterprise_classification") or _get_val("enterprise_type"),
            "major_activity": _get_val("major_activity"),
            "registration_date": _get_val("registration_date"),
        }
        claims.append((VerificationType.UDYAM, udyam_val, "udyam_registration_number", supp_udyam))

    # 4. MCA (CIN / LLPIN) Claim Discovery
    cin_val = _get_val("cin") or _get_val("llpin") or _get_val("company_identification_number")
    if cin_val:
        supp_mca = {
            "company_name": _get_val("company_name") or _get_val("legal_name") or _get_val("entity_name"),
            "company_type": _get_val("company_type") or _get_val("organization_type"),
            "date_of_incorporation": _get_val("date_of_incorporation") or _get_val("incorporation_date"),
            "registered_office_state": _get_val("registered_office_state") or _get_val("state"),
            "registered_office_address": _get_val("registered_office_address") or _get_val("address"),
        }
        claims.append((VerificationType.MCA, cin_val, "cin", supp_mca))

    # 5. Startup India (DPIIT) Claim Discovery
    startup_val = (
        _get_val("startup_india_number")
        or _get_val("startup_india_registration_number")
        or _get_val("dpiit_recognition_number")
        or _get_val("recognition_number")
        or _get_val("dipp_number")
    )
    if startup_val:
        supp_startup = {
            "entity_name": _get_val("entity_name") or _get_val("company_name") or _get_val("legal_name"),
            "recognition_date": _get_val("recognition_date"),
            "sector": _get_val("sector"),
            "startup_status": _get_val("startup_status") or _get_val("status"),
        }
        claims.append((VerificationType.STARTUP_INDIA, startup_val, "recognition_number", supp_startup))

    # 6. NSIC Registration Claim Discovery
    nsic_val = _get_val("nsic_registration_number") or _get_val("nsic_number")
    if nsic_val:
        supp_nsic = {
            "enterprise_name": _get_val("enterprise_name") or _get_val("company_name") or _get_val("legal_name"),
            "valid_from": _get_val("valid_from"),
            "valid_until": _get_val("valid_until"),
            "category": _get_val("category"),
            "products_services": _get_val("products_services"),
        }
        claims.append((VerificationType.NSIC, nsic_val, "nsic_registration_number", supp_nsic))

    # 7. EPFO Establishment Code Claim Discovery
    epfo_val = (
        _get_val("epfo_registration_number")
        or _get_val("epf_establishment_code")
        or _get_val("epfo_code")
        or _get_val("establishment_code")
    )
    if epfo_val:
        supp_epfo = {
            "establishment_name": _get_val("establishment_name") or _get_val("company_name") or _get_val("legal_name"),
            "state": _get_val("state"),
            "office_name": _get_val("office_name"),
        }
        claims.append((VerificationType.EPFO, epfo_val, "epfo_registration_number", supp_epfo))

    # 8. ESIC Registration Number Claim Discovery
    esic_val = (
        _get_val("esic_registration_number")
        or _get_val("employer_code")
        or _get_val("esic_code")
        or _get_val("esic_number")
    )
    if esic_val:
        supp_esic = {
            "employer_name": _get_val("employer_name") or _get_val("company_name") or _get_val("legal_name"),
            "state": _get_val("state"),
            "regional_office": _get_val("regional_office"),
            "registration_date": _get_val("registration_date"),
        }
        claims.append((VerificationType.ESIC, esic_val, "esic_registration_number", supp_esic))

    # 9. OEM Authorization Discovery
    oem_ref = (
        _get_val("reference_number")
        or _get_val("authorization_number")
        or _get_val("oem_authorization_number")
    )
    is_oem_doc = (
        proc.detected_document_type == DocumentClass.OEM_AUTHORIZATION
        or doc.document_type == "OEM_AUTHORIZATION"
        or _get_val("oem_name") is not None
    )
    if is_oem_doc:
        supp_oem = {
            "oem_name": _get_val("oem_name") or _get_val("manufacturer_name"),
            "authorized_entity": _get_val("authorized_entity") or _get_val("bidder_name") or _get_val("legal_name"),
            "product_scope": _get_val("product_scope") or _get_val("product_or_scope") or _get_val("product_name"),
            "valid_from": _get_val("valid_from"),
            "valid_until": _get_val("valid_until"),
            "signatory_name": _get_val("signatory_name"),
        }
        oem_val = oem_ref or _get_val("oem_name") or "OEM-AUTH-CLAIM"
        claims.append((VerificationType.OEM_AUTHORIZATION, oem_val, "oem_authorization", supp_oem))

    # 10. Local Content (MII) Declaration Discovery
    lc_pct = _get_val("local_content_percentage") or _get_val("percentage")
    is_lc_doc = (
        proc.detected_document_type == DocumentClass.LOCAL_CONTENT_DECLARATION
        or doc.document_type == "LOCAL_CONTENT_DECLARATION"
        or lc_pct is not None
    )
    if is_lc_doc:
        supp_lc = {
            "local_content_percentage": lc_pct,
            "supplier_class": _get_val("supplier_class") or _get_val("class"),
            "product_name": _get_val("product_name") or _get_val("product_or_scope"),
            "declaration_date": _get_val("declaration_date"),
            "certifying_authority": _get_val("certifying_authority"),
        }
        lc_ref = _get_val("reference_number") or lc_pct or "LOCAL-CONTENT-CLAIM"
        claims.append((VerificationType.LOCAL_CONTENT, lc_ref, "local_content", supp_lc))

    # 11. BIS Certificate Discovery
    bis_val = (
        _get_val("bis_registration_number")
        or _get_val("license_number")
        or _get_val("bis_license_number")
    )
    if bis_val:
        supp_bis = {
            "manufacturer_name": _get_val("manufacturer_name") or _get_val("company_name"),
            "standard_number": _get_val("standard_number") or _get_val("standard"),
            "product_name": _get_val("product_name") or _get_val("model_number"),
            "valid_from": _get_val("valid_from"),
            "valid_until": _get_val("valid_until"),
        }
        claims.append((VerificationType.BIS, bis_val, "bis_registration_number", supp_bis))

    # 12. Supporting Document Evidence Validation Discovery
    # Used for documents without external public registries (e.g. Turnover, Financial, Experience, Technical)
    if not claims:
        is_supporting = (
            proc.detected_document_type in [
                DocumentClass.TURNOVER_CERTIFICATE,
                DocumentClass.FINANCIAL_STATEMENT,
                DocumentClass.EXPERIENCE_CERTIFICATE,
                DocumentClass.TECHNICAL_DOCUMENT,
                DocumentClass.COMMERCIAL_DOCUMENT,
                DocumentClass.OTHER,
            ]
            or any(k in fields_dict for k in ["turnover", "net_worth", "udin", "experience_years", "ca_name", "scope_of_work"])
        )
        if is_supporting:
            supp_doc = {
                "reference_number": _get_val("reference_number") or _get_val("udin") or _get_val("certificate_number"),
                "issuer_name": _get_val("ca_name") or _get_val("issuer_name") or _get_val("authority_name") or _get_val("company_name"),
                "date": _get_val("date") or _get_val("issue_date") or _get_val("declaration_date"),
                "signatory_name": _get_val("signatory_name") or _get_val("partner_name") or _get_val("auditor_name"),
                "turnover": _get_val("turnover"),
                "net_worth": _get_val("net_worth"),
                "experience_years": _get_val("experience_years"),
                "product_name": _get_val("product_name"),
            }
            doc_ref = supp_doc["reference_number"] or "SUPPORTING-EVIDENCE-CLAIM"
            claims.append((VerificationType.SUPPORTING_DOCUMENT, doc_ref, "supporting_evidence", supp_doc))

    # Fallback to document class if fields were omitted but document class is specific
    if not claims:
        if proc.detected_document_type == DocumentClass.GST_CERTIFICATE:
            g_val = _get_val("gstin")
            if g_val:
                claims.append((VerificationType.GST, g_val, "gstin", {"legal_name": _get_val("legal_name")}))
        elif proc.detected_document_type == DocumentClass.PAN:
            p_val = _get_val("pan_number")
            if p_val:
                claims.append((VerificationType.PAN, p_val, "pan_number", {"name": _get_val("holder_name") or _get_val("name")}))
        elif proc.detected_document_type == DocumentClass.UDYAM_CERTIFICATE:
            u_val = _get_val("udyam_registration_number")
            if u_val:
                claims.append((VerificationType.UDYAM, u_val, "udyam_registration_number", {"enterprise_name": _get_val("enterprise_name")}))

    return claims


async def verify_document_claims(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    trigger_source: str = VerificationTriggerSource.BIDDER,
) -> VerificationTriggerResponse:
    """
    Triggers deterministic verification for all verifiable claims extracted from a BidDocument.
    - Enforces document active status.
    - Requires completed extraction / classification.
    - Idempotently resolves existing records or creates fresh attempts.
    - Persists verification telemetry, structured payloads, and evidence in PostgreSQL.
    """
    profile, bid, doc = _get_document_for_verification(db, current_user, bid_id, document_id)

    if not doc.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive or superseded documents cannot be verified.",
        )

    proc = doc.processing
    if not proc or proc.processing_stage != ProcessingStage.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document extraction is not completed yet. Please process the document first.",
        )

    claims = discover_claims_for_document(doc, proc)
    if not claims:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No verifiable structured claims (GSTIN, PAN, Udyam) found in this document.",
        )

    results_summary: List[VerificationSummaryItem] = []
    created_count = 0

    for v_type, claimed_val, field_key, supp_claims in claims:
        # 1. Idempotency Check: Check if an active record already exists with valid status
        existing = db.scalars(
            select(VerificationRecord).where(
                VerificationRecord.bid_id == bid.id,
                VerificationRecord.bid_document_id == doc.id,
                VerificationRecord.verification_type == v_type,
                VerificationRecord.claimed_value == claimed_val,
                VerificationRecord.is_active == True,
            )
        ).first()

        # If already VERIFIED or successfully evaluated with NOT_VERIFIED, return cached record
        if existing and existing.verification_status in [
            VerificationStatus.VERIFIED,
            VerificationStatus.NOT_VERIFIED,
            VerificationStatus.NEEDS_REVIEW,
        ]:
            results_summary.append(
                VerificationSummaryItem(
                    id=existing.id,
                    verification_type=existing.verification_type,
                    verification_status=existing.verification_status,
                    source_name=existing.source_name,
                    source_type=existing.source_type,
                    claimed_value=existing.claimed_value,
                    verified_value=existing.verified_value,
                    match_status=existing.match_status,
                    confidence=existing.confidence,
                    error_code=existing.error_code,
                    error_message=existing.error_message,
                    attempt_number=existing.attempt_number,
                    is_retryable=existing.verification_status in [VerificationStatus.UNAVAILABLE, VerificationStatus.FAILED],
                    evidence=existing.evidence,
                    verification_completed_at=existing.verification_completed_at,
                )
            )
            continue

        # 2. Initialize Record in DB
        v_record = existing or VerificationRecord(
            id=uuid.uuid4(),
            bid_id=bid.id,
            bid_document_id=doc.id,
            document_processing_id=proc.id if proc else None,
            verification_type=v_type,
            verification_status=VerificationStatus.PENDING,
            source_name="Pending Resolution",
            source_type="MOCK",
            claim_source=VerificationClaimSource.DOCUMENT,
            claimed_value=claimed_val,
            request_payload=supp_claims,
            attempt_number=1 if not existing else existing.attempt_number + 1,
            triggered_by_profile_id=profile.id if profile else None,
            trigger_source=trigger_source,
            verification_started_at=datetime.now(timezone.utc),
            is_active=True,
        )

        v_record.verification_status = VerificationStatus.IN_PROGRESS
        v_record.verification_started_at = datetime.now(timezone.utc)
        if not existing:
            db.add(v_record)
            created_count += 1
        db.commit()
        db.refresh(v_record)

        # 3. Dispatch to Verification Engine
        req = VerificationRequest(
            verification_type=v_type,
            claimed_value=claimed_val,
            claim_source=VerificationClaimSource.DOCUMENT,
            supporting_claims=supp_claims,
            bid_id=bid.id,
            bid_document_id=doc.id,
            document_processing_id=proc.id if proc else None,
            extra_context={"field_key": field_key, "original_filename": doc.original_filename},
        )

        exec_result: VerificationResult = await verification_engine.execute_verification(req)

        # 4. Update and Persist Outcome
        v_record.verification_status = exec_result.verification_status
        v_record.source_name = exec_result.source_name
        v_record.source_type = exec_result.source_type
        v_record.verified_value = str(exec_result.verified_value) if exec_result.verified_value is not None else None
        v_record.match_status = exec_result.match_status
        v_record.confidence = exec_result.confidence
        v_record.evidence = exec_result.evidence
        v_record.request_payload = exec_result.normalized_claim_payload or supp_claims
        v_record.response_payload = exec_result.normalized_verified_payload or exec_result.raw_response
        v_record.error_code = exec_result.error_code
        v_record.error_message = exec_result.error_message
        v_record.verification_completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(v_record)

        results_summary.append(
            VerificationSummaryItem(
                id=v_record.id,
                verification_type=v_record.verification_type,
                verification_status=v_record.verification_status,
                source_name=v_record.source_name,
                source_type=v_record.source_type,
                claimed_value=v_record.claimed_value,
                verified_value=v_record.verified_value,
                match_status=v_record.match_status,
                confidence=v_record.confidence,
                error_code=v_record.error_code,
                error_message=v_record.error_message,
                attempt_number=v_record.attempt_number,
                is_retryable=v_record.verification_status in [VerificationStatus.UNAVAILABLE, VerificationStatus.FAILED],
                evidence=v_record.evidence,
                verification_completed_at=v_record.verification_completed_at,
            )
        )

    return VerificationTriggerResponse(
        message=f"Claim verification completed for document '{doc.original_filename}'.",
        bid_id=bid.id,
        bid_document_id=doc.id,
        created_count=created_count,
        results=results_summary,
    )


def get_document_verifications(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DocumentVerificationListResponse:
    """
    Retrieves all verification records for a specific BidDocument.
    """
    _, bid, doc = _get_document_for_verification(db, current_user, bid_id, document_id)

    records = db.scalars(
        select(VerificationRecord)
        .where(
            VerificationRecord.bid_id == bid.id,
            VerificationRecord.bid_document_id == doc.id,
            VerificationRecord.is_active == True,
        )
        .order_by(VerificationRecord.created_at.asc())
    ).all()

    items = [
        VerificationSummaryItem(
            id=r.id,
            verification_type=r.verification_type,
            verification_status=r.verification_status,
            source_name=r.source_name,
            source_type=r.source_type,
            claimed_value=r.claimed_value,
            verified_value=r.verified_value,
            match_status=r.match_status,
            confidence=r.confidence,
            error_code=r.error_code,
            error_message=r.error_message,
            attempt_number=r.attempt_number,
            is_retryable=r.verification_status in [VerificationStatus.UNAVAILABLE, VerificationStatus.FAILED],
            evidence=r.evidence,
            verification_completed_at=r.verification_completed_at,
        )
        for r in records
    ]

    proc = doc.processing

    return DocumentVerificationListResponse(
        bid_id=bid.id,
        bid_document_id=doc.id,
        document_name=doc.document_name,
        detected_document_type=proc.detected_document_type if proc else None,
        total_verifications=len(items),
        verifications=items,
    )


def get_bid_verifications(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
) -> BidVerificationListResponse:
    """
    Aggregates all verification records across all active documents in a bid.
    Provides counts by status.
    """
    profile, bid = _get_bid_for_bidder(db, current_user, bid_id)

    records = db.scalars(
        select(VerificationRecord)
        .outerjoin(BidDocument, VerificationRecord.bid_document_id == BidDocument.id)
        .where(
            VerificationRecord.bid_id == bid.id,
            VerificationRecord.is_active == True,
            (VerificationRecord.bid_document_id == None) | (BidDocument.is_active == True),
        )
        .order_by(VerificationRecord.created_at.asc())
    ).all()

    items: List[VerificationSummaryItem] = []
    verified_count = 0
    not_verified_count = 0
    needs_review_count = 0
    unavailable_count = 0
    failed_count = 0
    pending_count = 0

    for r in records:
        if r.verification_status == VerificationStatus.VERIFIED:
            verified_count += 1
        elif r.verification_status == VerificationStatus.NOT_VERIFIED:
            not_verified_count += 1
        elif r.verification_status == VerificationStatus.NEEDS_REVIEW:
            needs_review_count += 1
        elif r.verification_status == VerificationStatus.UNAVAILABLE:
            unavailable_count += 1
        elif r.verification_status == VerificationStatus.FAILED:
            failed_count += 1
        elif r.verification_status in [VerificationStatus.PENDING, VerificationStatus.IN_PROGRESS]:
            pending_count += 1

        items.append(
            VerificationSummaryItem(
                id=r.id,
                verification_type=r.verification_type,
                verification_status=r.verification_status,
                source_name=r.source_name,
                source_type=r.source_type,
                claimed_value=r.claimed_value,
                verified_value=r.verified_value,
                match_status=r.match_status,
                confidence=r.confidence,
                error_code=r.error_code,
                error_message=r.error_message,
                attempt_number=r.attempt_number,
                is_retryable=r.verification_status in [VerificationStatus.UNAVAILABLE, VerificationStatus.FAILED],
                evidence=r.evidence,
                verification_completed_at=r.verification_completed_at,
            )
        )

    ready_for_compliance = (
        len(items) > 0
        and pending_count == 0
        and unavailable_count == 0
        and failed_count == 0
    )

    return BidVerificationListResponse(
        bid_id=bid.id,
        bid_number=bid.bid_number,
        total_verifications=len(items),
        verified_count=verified_count,
        not_verified_count=not_verified_count,
        needs_review_count=needs_review_count,
        unavailable_count=unavailable_count,
        failed_count=failed_count,
        pending_count=pending_count,
        verification_ready_for_compliance=ready_for_compliance,
        verifications=items,
    )


async def retry_verification_record(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    verification_id: uuid.UUID,
    trigger_source: str = VerificationTriggerSource.BIDDER,
) -> VerificationRetryResponse:
    """
    Retries an UNAVAILABLE or FAILED claim verification attempt.
    Increments attempt_number and updates record with latest outcome.
    """
    profile, bid = _get_bid_for_bidder(db, current_user, bid_id)

    record = db.scalars(
        select(VerificationRecord).where(
            VerificationRecord.id == verification_id,
            VerificationRecord.bid_id == bid.id,
            VerificationRecord.is_active == True,
        )
    ).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification record not found.",
        )

    if record.verification_status not in [VerificationStatus.UNAVAILABLE, VerificationStatus.FAILED, VerificationStatus.NEEDS_REVIEW]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Verification in status '{record.verification_status}' cannot be retried. Only UNAVAILABLE or FAILED records are eligible.",
        )

    # Update attempt telemetry
    record.attempt_number += 1
    record.verification_status = VerificationStatus.IN_PROGRESS
    record.verification_started_at = datetime.now(timezone.utc)
    record.error_code = None
    record.error_message = None
    db.commit()

    supp_claims = record.request_payload if isinstance(record.request_payload, dict) else {}

    req = VerificationRequest(
        verification_type=record.verification_type,
        claimed_value=record.claimed_value,
        claim_source=record.claim_source,
        supporting_claims=supp_claims,
        bid_id=bid.id,
        bid_document_id=record.bid_document_id,
        document_processing_id=record.document_processing_id,
    )

    exec_result: VerificationResult = await verification_engine.execute_verification(req)

    record.verification_status = exec_result.verification_status
    record.source_name = exec_result.source_name
    record.source_type = exec_result.source_type
    record.verified_value = str(exec_result.verified_value) if exec_result.verified_value is not None else None
    record.match_status = exec_result.match_status
    record.confidence = exec_result.confidence
    record.evidence = exec_result.evidence
    record.request_payload = exec_result.normalized_claim_payload or supp_claims
    record.response_payload = exec_result.normalized_verified_payload or exec_result.raw_response
    record.error_code = exec_result.error_code
    record.error_message = exec_result.error_message
    record.verification_completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(record)

    return VerificationRetryResponse(
        message=f"Verification retry completed for {record.verification_type} (attempt {record.attempt_number}).",
        verification=VerificationRecordResponse.model_validate(record),
    )


async def verify_bid_blacklisting(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    trigger_source: str = VerificationTriggerSource.BIDDER,
) -> VerificationTriggerResponse:
    """
    Executes Blacklisting and Debarment verification at the bidder/organization level for a bid.
    Queries Mock Blacklisting and Debarment registries using verified organization identifiers.
    Idempotent: updates existing active records or creates new ones.
    """
    profile, bid = _get_bid_for_bidder(db, current_user, bid_id)
    org: Optional[Organization] = bid.bidder_organization

    # Find blacklisting declaration if uploaded
    docs = db.scalars(
        select(BidDocument).where(
            BidDocument.bid_id == bid.id,
            BidDocument.is_active == True,
        )
    ).all()

    decl_val = "NOT_BLACKLISTED"
    decl_doc_id: Optional[uuid.UUID] = None
    for d in docs:
        if d.document_type == "BLACKLISTING_DECLARATION" or "blacklisting" in (d.document_name or "").lower():
            decl_doc_id = d.id
            if d.processing and d.processing.extracted_data and isinstance(d.processing.extracted_data, dict):
                fields = d.processing.extracted_data.get("fields", {})
                decl_val = fields.get("blacklisting_status", {}).get("value") or "NOT_BLACKLISTED"
            break

    supp_claims = {
        "entity_name": org.name if org else None,
        "pan": org.pan_number if org else None,
        "gstin": org.gstin if org else None,
        "cin": getattr(org, "cin", None),
        "udyam_number": getattr(org, "udyam_number", None),
        "blacklisting_declaration": decl_val,
    }

    results_summary: List[VerificationSummaryItem] = []
    created_count = 0

    for v_type in [VerificationType.BLACKLISTING, VerificationType.DEBARMENT]:
        existing = db.scalars(
            select(VerificationRecord).where(
                VerificationRecord.bid_id == bid.id,
                VerificationRecord.verification_type == v_type,
                VerificationRecord.is_active == True,
            )
        ).first()

        claimed_val = (
            org.pan_number
            if org and org.pan_number
            else (org.name if org else "BIDDER-ORG")
        )

        v_record = existing or VerificationRecord(
            id=uuid.uuid4(),
            bid_id=bid.id,
            bid_document_id=decl_doc_id,
            verification_type=v_type,
            verification_status=VerificationStatus.PENDING,
            source_name="Pending Resolution",
            source_type="MOCK",
            claim_source=VerificationClaimSource.PROFILE if not decl_doc_id else VerificationClaimSource.DOCUMENT,
            claimed_value=claimed_val,
            request_payload=supp_claims,
            attempt_number=1 if not existing else existing.attempt_number + 1,
            triggered_by_profile_id=profile.id if profile else None,
            trigger_source=trigger_source,
            verification_started_at=datetime.now(timezone.utc),
            is_active=True,
        )

        v_record.verification_status = VerificationStatus.IN_PROGRESS
        v_record.verification_started_at = datetime.now(timezone.utc)
        if not existing:
            db.add(v_record)
            created_count += 1
        db.commit()
        db.refresh(v_record)

        req = VerificationRequest(
            verification_type=v_type,
            claimed_value=claimed_val,
            claim_source=v_record.claim_source,
            supporting_claims=supp_claims,
            bid_id=bid.id,
            bid_document_id=decl_doc_id,
            extra_context={"bidder_name": org.name if org else None},
        )

        exec_result: VerificationResult = await verification_engine.execute_verification(req)

        v_record.verification_status = exec_result.verification_status
        v_record.source_name = exec_result.source_name
        v_record.source_type = exec_result.source_type
        v_record.verified_value = str(exec_result.verified_value) if exec_result.verified_value is not None else None
        v_record.match_status = exec_result.match_status
        v_record.confidence = exec_result.confidence
        v_record.evidence = exec_result.evidence
        v_record.request_payload = exec_result.normalized_claim_payload or supp_claims
        v_record.response_payload = exec_result.normalized_verified_payload or exec_result.raw_response
        v_record.error_code = exec_result.error_code
        v_record.error_message = exec_result.error_message
        v_record.verification_completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(v_record)

        results_summary.append(
            VerificationSummaryItem(
                id=v_record.id,
                verification_type=v_record.verification_type,
                verification_status=v_record.verification_status,
                source_name=v_record.source_name,
                source_type=v_record.source_type,
                claimed_value=v_record.claimed_value,
                verified_value=v_record.verified_value,
                match_status=v_record.match_status,
                confidence=v_record.confidence,
                error_code=v_record.error_code,
                error_message=v_record.error_message,
                attempt_number=v_record.attempt_number,
                is_retryable=v_record.verification_status in [VerificationStatus.UNAVAILABLE, VerificationStatus.FAILED],
                evidence=v_record.evidence,
                verification_completed_at=v_record.verification_completed_at,
            )
        )

    return VerificationTriggerResponse(
        message=f"Blacklisting and Debarment verification completed for bid '{bid.bid_number}'.",
        bid_id=bid.id,
        created_count=created_count,
        results=results_summary,
    )


async def verify_bid_consistency(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    trigger_source: str = VerificationTriggerSource.BIDDER,
) -> VerificationTriggerResponse:
    """
    Executes Cross-Document Consistency checking across all active extractions,
    verified registry records, and profile details for a bid.
    Stores outcome in VerificationRecord as CROSS_DOCUMENT.
    """
    from app.services.cross_document_consistency_service import consistency_engine

    profile, bid = _get_bid_for_bidder(db, current_user, bid_id)

    # 1. Run consistency evaluation
    v_status, match_status, findings, evidence_dict = consistency_engine.evaluate_bid_consistency(db=db, bid=bid)

    # 2. Upsert CROSS_DOCUMENT Verification Record
    existing = db.scalars(
        select(VerificationRecord).where(
            VerificationRecord.bid_id == bid.id,
            VerificationRecord.verification_type == VerificationType.CROSS_DOCUMENT,
            VerificationRecord.is_active == True,
        )
    ).first()

    v_record = existing or VerificationRecord(
        id=uuid.uuid4(),
        bid_id=bid.id,
        verification_type=VerificationType.CROSS_DOCUMENT,
        verification_status=VerificationStatus.PENDING,
        source_name="Cross-Document Consistency Engine",
        source_type=VerificationSourceType.INTERNAL,
        claim_source=VerificationClaimSource.CROSS_DOCUMENT,
        claimed_value="BID_IDENTITY_DATA",
        request_payload={"bid_id": str(bid.id)},
        attempt_number=1 if not existing else existing.attempt_number + 1,
        triggered_by_profile_id=profile.id if profile else None,
        trigger_source=trigger_source,
        verification_started_at=datetime.now(timezone.utc),
        is_active=True,
    )

    v_record.verification_status = v_status
    v_record.match_status = match_status
    v_record.verified_value = f"{evidence_dict['matched_checks']}/{evidence_dict['total_checks']} MATCHED"
    v_record.confidence = 1.0 if v_status == VerificationStatus.VERIFIED else 0.60
    v_record.evidence = evidence_dict
    v_record.response_payload = {"findings_count": len(findings), "status": v_status}
    v_record.error_code = None
    v_record.error_message = (
        f"{evidence_dict['review_required_checks']} consistency check(s) require review."
        if v_status == VerificationStatus.NEEDS_REVIEW and evidence_dict['review_required_checks'] > 0
        else None
    )
    v_record.verification_completed_at = datetime.now(timezone.utc)

    if not existing:
        db.add(v_record)
    db.commit()
    db.refresh(v_record)

    summary_item = VerificationSummaryItem(
        id=v_record.id,
        verification_type=v_record.verification_type,
        verification_status=v_record.verification_status,
        source_name=v_record.source_name,
        source_type=v_record.source_type,
        claimed_value=v_record.claimed_value,
        verified_value=v_record.verified_value,
        match_status=v_record.match_status,
        confidence=v_record.confidence,
        error_code=v_record.error_code,
        error_message=v_record.error_message,
        attempt_number=v_record.attempt_number,
        is_retryable=False,
        evidence=v_record.evidence,
        verification_completed_at=v_record.verification_completed_at,
    )

    return VerificationTriggerResponse(
        message=f"Cross-document consistency check completed for bid '{bid.bid_number}'.",
        bid_id=bid.id,
        created_count=1 if not existing else 0,
        results=[summary_item],
    )


def get_bid_consistency_report(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
) -> Dict[str, Any]:
    """
    Retrieves the latest Cross-Document Consistency Report for a bid.
    """
    from app.services.cross_document_consistency_service import consistency_engine

    profile, bid = _get_bid_for_bidder(db, current_user, bid_id)
    v_status, match_status, findings, evidence_dict = consistency_engine.evaluate_bid_consistency(db=db, bid=bid)

    return {
        "bid_id": str(bid.id),
        "bid_number": bid.bid_number,
        "verification_status": v_status,
        "overall_match_status": match_status,
        "total_checks": evidence_dict["total_checks"],
        "matched_checks": evidence_dict["matched_checks"],
        "review_required_checks": evidence_dict["review_required_checks"],
        "findings": [f.model_dump() for f in findings],
        "evaluated_at": evidence_dict["evaluated_at"],
    }
