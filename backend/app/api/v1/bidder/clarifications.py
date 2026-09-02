"""
Bidder Clarification API Router
Part 16 — Clarification Request Workflow for BidVerify AI
Provides authenticated endpoints for Bidders to view clarification requests,
submit textual responses, and upload supporting / replacement evidence through
the existing Document AI and quality check pipelines.
"""

import hashlib
from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authorization import require_role
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.clarification import ClarificationRequest, ClarificationStatus
from app.db.models.document_processing import DocumentProcessing, ExtractionMethod, ProcessingStage, ProcessingStatus
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.bid_document import BidDocumentResponse
from app.schemas.clarification import (
    ClarificationRequestDetailResponse,
    ClarificationRequestListResponse,
    ClarificationResponseCreate,
    ClarificationResponseDTO,
    ClarificationSummaryResponse,
)
from app.services.bid_document_service import validate_file_safety
from app.services.clarification_service import ClarificationService
from app.services.document_processing_service import DocumentProcessingService
from app.services.document_quality_service import DocumentQualityService
from app.services.storage_service import sanitize_filename, storage_service

router = APIRouter()


@router.get(
    "",
    response_model=ClarificationRequestListResponse,
    summary="List bidder clarification requests",
)
def list_bidder_clarifications(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    tender_id: Optional[uuid.UUID] = Query(None, description="Filter by tender ID"),
    status: Optional[str] = Query(None, description="Filter by status (SENT, VIEWED, RESPONDED, UNDER_REVIEW, RESOLVED, CLOSED, EXPIRED)"),
    priority: Optional[str] = Query(None, description="Filter by priority (LOW, NORMAL, HIGH, URGENT)"),
    type: Optional[str] = Query(None, description="Filter by clarification type"),
    search: Optional[str] = Query(None, description="Search keyword in subject or message"),
    current_user: User = Depends(require_role(["BIDDER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Lists paginated clarification requests sent to the Bidder's organization.
    """
    org_id = current_user.profile.organization_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have an associated organization.",
        )

    return ClarificationService.list_bidder_clarifications(
        db=db,
        organization_id=org_id,
        tender_id=tender_id,
        status_filter=status,
        priority_filter=priority,
        type_filter=type,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/summary",
    response_model=ClarificationSummaryResponse,
    summary="Get bidder clarification summary counters",
)
def get_bidder_clarification_summary(
    tender_id: Optional[uuid.UUID] = Query(None, description="Filter by tender ID"),
    current_user: User = Depends(require_role(["BIDDER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Returns summary counters for the Bidder.
    """
    org_id = current_user.profile.organization_id
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have an associated organization.",
        )

    return ClarificationService.get_clarification_summary(
        db=db,
        organization_id=org_id,
        tender_id=tender_id,
        is_bidder=True,
    )


@router.get(
    "/{id}",
    response_model=ClarificationRequestDetailResponse,
    summary="Get clarification request detail for bidder",
)
def get_bidder_clarification_detail(
    id: uuid.UUID,
    current_user: User = Depends(require_role(["BIDDER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Retrieves full clarification detail. Automatically marks status as VIEWED if previously SENT.
    """
    return ClarificationService.get_clarification_detail(
        db=db,
        clarification_id=id,
        current_profile=current_user.profile,
    )


@router.post(
    "/{id}/respond",
    response_model=ClarificationResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Submit bidder response to clarification",
)
def respond_to_clarification(
    id: uuid.UUID,
    payload: ClarificationResponseCreate,
    current_user: User = Depends(require_role(["BIDDER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Submits a response to a clarification request with text and optional attached/replacement document.
    """
    resp = ClarificationService.respond_to_clarification(
        db=db,
        clarification_id=id,
        current_profile=current_user.profile,
        payload=payload,
    )

    resp_name = f"{resp.responded_by.first_name} {resp.responded_by.last_name}".strip() if resp.responded_by else "Bidder Representative"
    doc_name = resp.attached_document.original_filename if resp.attached_document else None
    rep_name = resp.replaced_document.original_filename if resp.replaced_document else None

    return ClarificationResponseDTO(
        id=resp.id,
        clarification_request_id=resp.clarification_request_id,
        responded_by_profile_id=resp.responded_by_profile_id,
        responded_by_name=resp_name,
        response_text=resp.response_text,
        attached_document_id=resp.attached_document_id,
        attached_document_name=doc_name,
        is_replacement_document=resp.is_replacement_document,
        replaced_document_id=resp.replaced_document_id,
        replaced_document_name=rep_name,
        metadata_json=resp.metadata_json,
        created_at=resp.created_at,
        updated_at=resp.updated_at,
    )


@router.post(
    "/{id}/upload-document",
    response_model=BidDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a supporting or replacement document for clarification",
)
def upload_clarification_document(
    id: uuid.UUID,
    file: UploadFile = File(...),
    document_type: str = Form("SUPPORTING_DOCUMENT"),
    notes: Optional[str] = Form(None),
    is_replacement: bool = Form(False),
    replaced_document_id: Optional[uuid.UUID] = Form(None),
    current_user: User = Depends(require_role(["BIDDER", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Uploads a new or replacement document in context of a clarification request.
    Executes Document AI and Quality assessment pipelines immediately.
    """
    req = db.scalars(select(ClarificationRequest).where(ClarificationRequest.id == id)).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clarification not found.")

    if current_user.profile.organization_id != req.bidder_organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized.")

    # Read and validate file safety
    try:
        content = file.file.read()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to read uploaded file.")
    validate_file_safety(file, content)

    # Calculate version and replacement logic
    next_version = 1
    target_req_id = req.related_requirement_id

    rep_doc_id = replaced_document_id or req.related_document_id
    if is_replacement and rep_doc_id:
        prior_doc = db.scalars(select(BidDocument).where(BidDocument.id == rep_doc_id)).first()
        if prior_doc:
            next_version = prior_doc.version + 1
            if prior_doc.tender_requirement_id:
                target_req_id = prior_doc.tender_requirement_id

    doc_id = uuid.uuid4()
    original_filename = file.filename or f"{document_type.lower()}.pdf"
    safe_name = sanitize_filename(original_filename)
    storage_path = f"bids/{req.bid_id}/{doc_id}/{safe_name}"
    mime_type = file.content_type or "application/octet-stream"

    # Persist in storage
    try:
        storage_service.upload_file(
            storage_path=storage_path,
            content=content,
            content_type=mime_type,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Storage service error during document upload.",
        )

    file_sha256 = hashlib.sha256(content).hexdigest()
    new_doc = BidDocument(
        id=doc_id,
        bid_id=req.bid_id,
        tender_requirement_id=target_req_id,
        uploaded_by_profile_id=current_user.profile.id,
        document_type=document_type.upper(),
        document_name=req.subject[:255] if req.subject else document_type.upper(),
        original_filename=original_filename,
        storage_path=storage_path,
        mime_type=mime_type,
        file_size=len(content),
        status="UPLOADED",
        file_hash=file_sha256,
        version=next_version,
        notes=notes or f"Uploaded in response to clarification '{req.subject}'",
        is_active=True,
    )
    db.add(new_doc)
    db.flush()

    # Create initial DocumentProcessing record
    initial_processing = DocumentProcessing(
        id=uuid.uuid4(),
        bid_document_id=doc_id,
        stage=ProcessingStage.PENDING,
        status=ProcessingStatus.PENDING,
        extraction_method=ExtractionMethod.HYBRID,
        storage_path=storage_path,
    )
    db.add(initial_processing)
    db.commit()
    db.refresh(new_doc)

    # Trigger async/sync document processing and quality assessment
    try:
        DocumentProcessingService.process_document(db=db, document_id=doc_id)
        DocumentQualityService.assess_document_quality(db=db, document_id=doc_id)
    except Exception as exc:
        logger.warning(f"Error processing clarification uploaded document {doc_id}: {exc}")

    # Generate signed download URL
    signed_url = None
    try:
        signed_url = storage_service.get_download_url(new_doc.storage_path, expires_in=3600)
    except Exception:
        pass

    return BidDocumentResponse(
        id=new_doc.id,
        bid_id=new_doc.bid_id,
        tender_requirement_id=new_doc.tender_requirement_id,
        uploaded_by_profile_id=new_doc.uploaded_by_profile_id,
        document_type=new_doc.document_type,
        document_name=new_doc.document_name,
        original_filename=new_doc.original_filename,
        mime_type=new_doc.mime_type,
        file_size=new_doc.file_size,
        status=new_doc.status,
        version=new_doc.version,
        notes=new_doc.notes,
        is_active=new_doc.is_active,
        uploaded_at=new_doc.created_at,
        updated_at=new_doc.updated_at,
        download_url=signed_url,
    )
