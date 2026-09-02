"""
Bidder Certificate Validity API Router
Part 14 — Certificate Validity Monitoring for BidVerify AI
Provides authenticated endpoints for bidders to view certificate validity,
trigger re-checks, and manage replacement documents.
"""

from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authorization import require_role
from app.db.models.bid_document import BidDocument
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.certificate_validity import (
    BidderCertificateListResponse,
    CertificateValidityRecheckResponse,
    DocumentValidityDTO,
)
from app.services.certificate_validity_service import CertificateValidityService

router = APIRouter()


@router.get("/validity", response_model=BidderCertificateListResponse)
def get_bidder_certificates_validity(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by validity status (VALID, EXPIRING_SOON, EXPIRED, NO_EXPIRY, UNKNOWN, REVIEW_REQUIRED)"),
    search: Optional[str] = Query(None, description="Search keyword in document name or evidence snippet"),
    current_user: User = Depends(require_role(["BIDDER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Lists paginated certificate validity records and aggregate health statistics
    for the authenticated bidder's organization.
    """
    if not current_user.profile or not current_user.profile.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticated user is not associated with an active organization.",
        )

    org_id = current_user.profile.organization_id

    result = CertificateValidityService.get_bidder_certificates(
        db=db,
        organization_id=org_id,
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

    return BidderCertificateListResponse(
        items=items_dto,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
        stats=result["stats"],
    )


@router.get("/documents/{document_id}/validity", response_model=DocumentValidityDTO)
def get_document_validity_detail(
    document_id: uuid.UUID,
    current_user: User = Depends(require_role(["BIDDER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Retrieves the current validity record and extraction details for a single document.
    Enforces organization-level tenant isolation.
    """
    doc = db.scalars(
        select(BidDocument).where(BidDocument.id == document_id)
    ).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # Security tenant isolation
    user_role = current_user.profile.role.name.upper() if current_user.profile and current_user.profile.role else ""
    if user_role != "ADMIN" and doc.organization_id != current_user.profile.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to document from another organization.",
        )

    record = CertificateValidityService.evaluate_document_validity(
        db=db,
        document_id=document_id,
        force_recheck=False,
        current_user=current_user,
    )

    return DocumentValidityDTO(
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


@router.post("/documents/{document_id}/validity/recheck", response_model=CertificateValidityRecheckResponse)
def recheck_document_validity(
    document_id: uuid.UUID,
    current_user: User = Depends(require_role(["BIDDER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Forces a fresh re-evaluation of certificate validity for a document.
    """
    doc = db.scalars(
        select(BidDocument).where(BidDocument.id == document_id)
    ).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    user_role = current_user.profile.role.name.upper() if current_user.profile and current_user.profile.role else ""
    if user_role != "ADMIN" and doc.organization_id != current_user.profile.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to document from another organization.",
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
