"""
Procurement Certificate Validity API Router
Part 14 — Certificate Validity Monitoring for BidVerify AI
Provides authenticated endpoints for Procurement Officers and Admins
to inspect certificate validity across tenders and bids, recheck dates,
and trigger periodic batch monitoring.
"""

from datetime import date
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authorization import require_role
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.tender import Tender
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.certificate_validity import (
    CertificateValidityRecheckResponse,
    DocumentValidityDTO,
    PeriodicValidityCheckResponse,
    ProcurementCertificateListResponse,
)
from app.services.certificate_validity_service import CertificateValidityService

router = APIRouter()


@router.get("/validity", response_model=ProcurementCertificateListResponse)
def get_procurement_certificates_validity(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    tender_id: Optional[uuid.UUID] = Query(None, description="Filter by tender ID"),
    bid_id: Optional[uuid.UUID] = Query(None, description="Filter by bid ID"),
    status: Optional[str] = Query(None, description="Filter by validity status (VALID, EXPIRING_SOON, EXPIRED, NO_EXPIRY, UNKNOWN, REVIEW_REQUIRED)"),
    search: Optional[str] = Query(None, description="Search keyword in document name or evidence snippet"),
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Lists paginated certificate validity records for procurement evaluation.
    Scoping: PROCUREMENT_OFFICER is restricted to tenders owned by their tenant organization.
    """
    user_role = current_user.profile.role.name.upper() if current_user.profile and current_user.profile.role else ""
    user_org_id = current_user.profile.organization_id if current_user.profile else None

    # Check tender ownership for procurement officer
    if user_role == "PROCUREMENT_OFFICER":
        if tender_id:
            t = db.scalars(select(Tender).where(Tender.id == tender_id)).first()
            if not t or t.organization_id != user_org_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tender not found or unauthorized.",
                )
        elif bid_id:
            b = db.scalars(select(Bid).where(Bid.id == bid_id)).first()
            if not b:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bid not found.")
            t = db.scalars(select(Tender).where(Tender.id == b.tender_id)).first()
            if not t or t.organization_id != user_org_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bid not found or unauthorized.")

    result = CertificateValidityService.get_procurement_certificates(
        db=db,
        tender_id=tender_id,
        bid_id=bid_id,
        organization_id=user_org_id if user_role == "PROCUREMENT_OFFICER" and not tender_id and not bid_id else None,
        status_filter=status,
        search=search,
        page=page,
        page_size=page_size,
    )

    items_dto = [
        DocumentValidityDTO(
            id=rec.id,
            document_id=rec.document_id,
            bid_id=rec.bid_id,
            organization_id=rec.organization_id,
            document_name=rec.document.document_name if rec.document else None,
            document_type=rec.document_type,
            issue_date=rec.issue_date,
            expiry_date=rec.expiry_date,
            validity_status=rec.validity_status,
            days_until_expiry=rec.days_until_expiry,
            date_source=rec.date_source,
            source_page=rec.source_page,
            source_text=rec.source_text,
            confidence=rec.confidence,
            is_current=rec.is_current,
            submission_validity_status=rec.submission_validity_status,
            last_checked_at=rec.last_checked_at,
            next_check_at=rec.next_check_at,
            metadata_json=rec.metadata_json or {},
            created_at=rec.created_at,
            updated_at=rec.updated_at,
        )
        for rec in result["items"]
    ]

    return ProcurementCertificateListResponse(
        items=items_dto,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )


@router.get("/bids/{bid_id}/certificate-validity", response_model=ProcurementCertificateListResponse)
def get_bid_certificates_validity(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Returns all certificate validity records for a specific bid package.
    """
    user_role = current_user.profile.role.name.upper() if current_user.profile and current_user.profile.role else ""
    user_org_id = current_user.profile.organization_id if current_user.profile else None

    bid = db.scalars(select(Bid).where(Bid.id == bid_id)).first()
    if not bid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bid not found.")

    if user_role == "PROCUREMENT_OFFICER":
        tender = db.scalars(select(Tender).where(Tender.id == bid.tender_id)).first()
        if not tender or tender.organization_id != user_org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bid not found or unauthorized.")

    result = CertificateValidityService.get_procurement_certificates(
        db=db,
        bid_id=bid_id,
        page=1,
        page_size=100,
    )

    items_dto = [
        DocumentValidityDTO(
            id=rec.id,
            document_id=rec.document_id,
            bid_id=rec.bid_id,
            organization_id=rec.organization_id,
            document_name=rec.document.document_name if rec.document else None,
            document_type=rec.document_type,
            issue_date=rec.issue_date,
            expiry_date=rec.expiry_date,
            validity_status=rec.validity_status,
            days_until_expiry=rec.days_until_expiry,
            date_source=rec.date_source,
            source_page=rec.source_page,
            source_text=rec.source_text,
            confidence=rec.confidence,
            is_current=rec.is_current,
            submission_validity_status=rec.submission_validity_status,
            last_checked_at=rec.last_checked_at,
            next_check_at=rec.next_check_at,
            metadata_json=rec.metadata_json or {},
            created_at=rec.created_at,
            updated_at=rec.updated_at,
        )
        for rec in result["items"]
    ]

    return ProcurementCertificateListResponse(
        items=items_dto,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )


@router.post("/documents/{document_id}/validity/recheck", response_model=CertificateValidityRecheckResponse)
def procurement_recheck_document_validity(
    document_id: uuid.UUID,
    current_user: User = Depends(require_role(["PROCUREMENT_OFFICER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Forces a fresh re-evaluation of certificate validity on an evaluated bid document.
    """
    doc = db.scalars(
        select(BidDocument).where(BidDocument.id == document_id)
    ).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    record = CertificateValidityService.evaluate_document_validity(
        db=db,
        document_id=document_id,
        force_recheck=True,
        current_user=current_user,
    )

    dto = DocumentValidityDTO(
        id=record.id,
        document_id=record.document_id,
        bid_id=record.bid_id,
        organization_id=record.organization_id,
        document_name=doc.document_name,
        document_type=record.document_type,
        issue_date=record.issue_date,
        expiry_date=record.expiry_date,
        validity_status=record.validity_status,
        days_until_expiry=record.days_until_expiry,
        date_source=record.date_source,
        source_page=record.source_page,
        source_text=record.source_text,
        confidence=record.confidence,
        is_current=record.is_current,
        submission_validity_status=record.submission_validity_status,
        last_checked_at=record.last_checked_at,
        next_check_at=record.next_check_at,
        metadata_json=record.metadata_json or {},
        created_at=record.created_at,
        updated_at=record.updated_at,
    )

    return CertificateValidityRecheckResponse(
        record=dto,
        message=f"Certificate validity successfully rechecked: {record.validity_status}",
    )


@router.post("/periodic-check", response_model=PeriodicValidityCheckResponse)
def trigger_periodic_validity_check(
    reference_date: Optional[str] = Query(None, description="Optional ISO date YYYY-MM-DD for simulation"),
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Triggers batch re-check of all active certificate validity records across the platform.
    Restricted to system administrators.
    """
    ref_d = None
    if reference_date:
        try:
            ref_d = date.fromisoformat(reference_date)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD.")

    result = CertificateValidityService.run_periodic_validity_checks(
        db=db,
        reference_date=ref_d,
    )

    return PeriodicValidityCheckResponse(
        total_checked=result["total_checked"],
        status_transitions=result["status_transitions"],
        status_breakdown=result["status_breakdown"],
        reference_date=result["reference_date"],
    )
