"""
Bid Document Service for Part 3D: Bid Document Upload
Handles secure file validation, private storage persistence, requirement mapping,
document replacement/removal, and ownership enforcement.
"""

import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Set, Tuple
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import settings
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.document_processing import (
    DocumentProcessing,
    ExtractionMethod,
    ProcessingStage,
    ProcessingStatus,
)
from app.db.models.profile import Profile
from app.db.models.tender import Tender
from app.db.models.tender_requirement import TenderRequirement
from app.db.models.user import User
from app.schemas.bid_document import (
    BidDocumentDownloadResponse,
    BidDocumentListResponse,
    BidDocumentResponse,
    BidDocumentsSummary,
)
from app.schemas.document_processing import DocumentProcessingResponse
from app.services.bid_service import validate_tender_for_bid_creation
from app.services.bidder_profile_service import _get_or_create_user_organization
from app.services.storage_service import sanitize_filename, storage_service

# Safe document extensions allowed for upload
ALLOWED_EXTENSIONS: Set[str] = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
}

# Dangerous executable extensions strictly rejected
BLOCKED_EXTENSIONS: Set[str] = {
    ".exe",
    ".bat",
    ".cmd",
    ".ps1",
    ".js",
    ".sh",
    ".vbs",
    ".py",
    ".bin",
    ".dll",
    ".com",
    ".scr",
    ".msi",
}

ALLOWED_MIME_TYPES: Set[str] = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/pjpeg",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
}


def validate_file_safety(file: UploadFile, content: bytes) -> None:
    """
    Validates file size limit, safe extension, and MIME type.
    Rejects empty files, oversized files, and executable formats.
    """
    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty. Please select a valid document.",
        )

    # 1. File Size Limit
    if len(content) > settings.MAX_FILE_SIZE_BYTES:
        max_mb = settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {max_mb} MB.",
        )

    # 2. File Extension
    filename = file.filename or "unknown"
    _, ext = os.path.splitext(filename.lower())

    if ext in BLOCKED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Executable and script files ({ext}) are strictly prohibited.",
        )

    if ext not in ALLOWED_EXTENSIONS:
        allowed_str = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed formats: {allowed_str}",
        )

    # 3. MIME Type check (if provided by client)
    content_type = (file.content_type or "").lower().split(";")[0].strip()
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        # Fallback check for standard pdf/images if client mislabels
        if ext == ".pdf" and content_type in ["application/x-pdf", "binary/octet-stream"]:
            pass
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid MIME type '{content_type}' for document.",
            )


def _get_bid_for_bidder(db: Session, current_user: User, bid_id: uuid.UUID) -> Tuple[Profile, Bid]:
    """
    Retrieves a bid and verifies that it belongs to the authenticated bidder's organization.
    Returns 404 on non-existent or cross-tenant access to avoid data leakage.
    """
    profile, org = _get_or_create_user_organization(db, current_user)

    bid = db.scalars(
        select(Bid)
        .options(
            joinedload(Bid.tender).joinedload(Tender.organization),
            joinedload(Bid.tender).selectinload(Tender.requirements),
        )
        .where(
            and_(
                Bid.id == bid_id,
                Bid.bidder_organization_id == org.id,
                Bid.is_active == True,
            )
        )
    ).first()

    if not bid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bid submission record not found.",
        )

    return profile, bid


def _validate_bid_editable(bid: Bid) -> None:
    """Verifies that the bid is in DRAFT status and the tender remains eligible for preparation."""
    if bid.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Documents can only be added or modified on DRAFT bids. Current status is '{bid.status}'.",
        )

    # Verify tender status and deadline
    validate_tender_for_bid_creation(bid.tender)


def _format_document_response(doc: BidDocument) -> BidDocumentResponse:
    """Formats a BidDocument model instance into BidDocumentResponse schema."""
    signed_url = storage_service.create_signed_url(doc.storage_path, expires_in_seconds=300)

    req_code = None
    req_name = None
    is_mandatory = None
    if doc.tender_requirement:
        req_code = doc.tender_requirement.code
        req_name = doc.tender_requirement.name
        is_mandatory = doc.tender_requirement.is_mandatory

    processing_data = None
    if doc.processing:
        processing_data = DocumentProcessingResponse.model_validate(doc.processing)

    return BidDocumentResponse(
        id=doc.id,
        bid_id=doc.bid_id,
        tender_requirement_id=doc.tender_requirement_id,
        uploaded_by_profile_id=doc.uploaded_by_profile_id,
        document_type=doc.document_type,
        document_name=doc.document_name,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        file_size=doc.file_size,
        status=doc.status,
        version=doc.version,
        notes=doc.notes,
        is_active=doc.is_active,
        uploaded_at=doc.created_at,
        updated_at=doc.updated_at,
        download_url=signed_url,
        requirement_code=req_code,
        requirement_name=req_name,
        is_mandatory=is_mandatory,
        processing=processing_data,
    )


def upload_bid_document(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    file: UploadFile,
    document_type: str,
    tender_requirement_id: Optional[uuid.UUID] = None,
    notes: Optional[str] = None,
) -> BidDocumentResponse:
    """
    Uploads a compliance document for a draft bid.
    Performs safety validations, requirement verification, stores file in private storage,
    and handles versioning/replacement if a prior document exists for the requirement.
    """
    profile, bid = _get_or_create_bid_ownership(db, current_user, bid_id)
    _validate_bid_editable(bid)

    # 1. Read and validate file content
    try:
        content = file.file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file.",
        )
    validate_file_safety(file, content)

    # 2. Verify tender requirement if linked
    req = None
    document_name = document_type.replace("_", " ").title()

    if tender_requirement_id:
        req = db.scalars(
            select(TenderRequirement).where(
                and_(
                    TenderRequirement.id == tender_requirement_id,
                    TenderRequirement.tender_id == bid.tender_id,
                    TenderRequirement.is_active == True,
                )
            )
        ).first()
        if not req:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The specified tender requirement is invalid or does not belong to this tender.",
            )
        document_name = req.name

    # 3. Check for existing active document for this requirement/type in this bid
    existing_active_doc = None
    next_version = 1

    if tender_requirement_id:
        existing_active_doc = db.scalars(
            select(BidDocument).where(
                and_(
                    BidDocument.bid_id == bid.id,
                    BidDocument.tender_requirement_id == tender_requirement_id,
                    BidDocument.is_active == True,
                )
            )
        ).first()
    else:
        existing_active_doc = db.scalars(
            select(BidDocument).where(
                and_(
                    BidDocument.bid_id == bid.id,
                    BidDocument.document_type == document_type,
                    BidDocument.tender_requirement_id.is_(None),
                    BidDocument.is_active == True,
                )
            )
        ).first()

    if existing_active_doc:
        next_version = existing_active_doc.version + 1
        existing_active_doc.is_active = False
        existing_active_doc.status = "REPLACED"

    # 4. Generate safe unique storage path
    doc_id = uuid.uuid4()
    original_filename = file.filename or f"{document_type.lower()}.pdf"
    safe_name = sanitize_filename(original_filename)
    storage_path = f"bids/{bid.id}/{doc_id}/{safe_name}"

    # 5. Persist to storage
    mime_type = file.content_type or "application/octet-stream"
    try:
        storage_service.upload_file(
            storage_path=storage_path,
            content=content,
            content_type=mime_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Storage service error during document upload.",
        )

    # 6. Create database record
    file_sha256 = hashlib.sha256(content).hexdigest()
    new_doc = BidDocument(
        id=doc_id,
        bid_id=bid.id,
        tender_requirement_id=tender_requirement_id,
        uploaded_by_profile_id=profile.id,
        document_type=document_type.upper(),
        document_name=document_name,
        original_filename=original_filename,
        storage_path=storage_path,
        mime_type=mime_type,
        file_size=len(content),
        file_hash=file_sha256,
        status="UPLOADED",
        version=next_version,
        notes=notes,
        is_active=True,
    )

    db.add(new_doc)
    db.commit()

    # Create DocumentProcessing record for Part 4A
    proc = DocumentProcessing(
        id=uuid.uuid4(),
        bid_document_id=new_doc.id,
        processing_status=ProcessingStatus.QUEUED,
        processing_stage=ProcessingStage.INGESTION,
        extraction_method=ExtractionMethod.NONE,
    )
    db.add(proc)
    db.commit()
    db.refresh(new_doc)

    # Eager load requirement and processing for response
    new_doc = db.scalars(
        select(BidDocument)
        .options(
            joinedload(BidDocument.tender_requirement),
            joinedload(BidDocument.processing),
        )
        .where(BidDocument.id == new_doc.id)
    ).one()

    return _format_document_response(new_doc)


def _get_or_create_bid_ownership(db: Session, current_user: User, bid_id: uuid.UUID) -> Tuple[Profile, Bid]:
    return _get_bid_for_bidder(db, current_user, bid_id)


def list_bid_documents(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    include_inactive: bool = False,
) -> BidDocumentListResponse:
    """
    Returns all uploaded documents for a bid and computes real-time readiness progress
    against the tender's mandatory document requirements.
    """
    profile, bid = _get_bid_for_bidder(db, current_user, bid_id)

    query = (
        select(BidDocument)
        .options(
            joinedload(BidDocument.tender_requirement),
            joinedload(BidDocument.processing),
        )
        .where(BidDocument.bid_id == bid.id)
    )
    if not include_inactive:
        query = query.where(BidDocument.is_active == True)

    docs = db.scalars(query.order_by(BidDocument.created_at.desc())).all()

    # Calculate required document counts based on TenderRequirements
    active_docs = [d for d in docs if d.is_active]
    uploaded_req_ids = {d.tender_requirement_id for d in active_docs if d.tender_requirement_id}

    required_reqs = [
        r for r in bid.tender.requirements
        if r.is_active and (r.is_mandatory or r.requirement_type == "DOCUMENT")
    ]
    total_required = len(required_reqs)
    uploaded_required = sum(1 for r in required_reqs if r.id in uploaded_req_ids)
    missing_required = max(0, total_required - uploaded_required)
    is_ready = missing_required == 0

    summary = BidDocumentsSummary(
        total_required=total_required,
        uploaded_required=uploaded_required,
        missing_required=missing_required,
        total_uploaded=len(active_docs),
        is_ready_for_submission=is_ready,
    )

    items = [_format_document_response(d) for d in docs]

    return BidDocumentListResponse(
        items=items,
        summary=summary,
    )


def get_bid_document(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
) -> BidDocumentResponse:
    """Retrieves metadata and secure signed access URL for a specific uploaded document."""
    profile, bid = _get_bid_for_bidder(db, current_user, bid_id)

    doc = db.scalars(
        select(BidDocument)
        .options(
            joinedload(BidDocument.tender_requirement),
            joinedload(BidDocument.processing),
        )
        .where(
            and_(
                BidDocument.id == document_id,
                BidDocument.bid_id == bid.id,
            )
        )
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return _format_document_response(doc)


def replace_bid_document(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    file: UploadFile,
    notes: Optional[str] = None,
) -> BidDocumentResponse:
    """
    Replaces an active document with a new version.
    Marks old document as REPLACED/inactive and creates a new active version.
    """
    profile, bid = _get_bid_for_bidder(db, current_user, bid_id)
    _validate_bid_editable(bid)

    old_doc = db.scalars(
        select(BidDocument).where(
            and_(
                BidDocument.id == document_id,
                BidDocument.bid_id == bid.id,
                BidDocument.is_active == True,
            )
        )
    ).first()

    if not old_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active document not found for replacement.",
        )

    # Read and validate new file
    try:
        content = file.file.read()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file.",
        )
    validate_file_safety(file, content)

    # Mark previous as replaced
    old_doc.is_active = False
    old_doc.status = "REPLACED"

    # Upload new file
    new_id = uuid.uuid4()
    original_filename = file.filename or old_doc.original_filename
    safe_name = sanitize_filename(original_filename)
    storage_path = f"bids/{bid.id}/{new_id}/{safe_name}"
    mime_type = file.content_type or "application/octet-stream"

    storage_service.upload_file(
        storage_path=storage_path,
        content=content,
        content_type=mime_type,
    )

    file_sha256 = hashlib.sha256(content).hexdigest()
    new_doc = BidDocument(
        id=new_id,
        bid_id=bid.id,
        tender_requirement_id=old_doc.tender_requirement_id,
        uploaded_by_profile_id=profile.id,
        document_type=old_doc.document_type,
        document_name=old_doc.document_name,
        original_filename=original_filename,
        storage_path=storage_path,
        mime_type=mime_type,
        file_size=len(content),
        file_hash=file_sha256,
        status="UPLOADED",
        version=old_doc.version + 1,
        notes=notes or old_doc.notes,
        is_active=True,
    )

    db.add(new_doc)
    db.commit()

    # Create DocumentProcessing record for new document version
    proc = DocumentProcessing(
        id=uuid.uuid4(),
        bid_document_id=new_doc.id,
        processing_status=ProcessingStatus.QUEUED,
        processing_stage=ProcessingStage.INGESTION,
        extraction_method=ExtractionMethod.NONE,
    )
    db.add(proc)
    db.commit()
    db.refresh(new_doc)

    new_doc = db.scalars(
        select(BidDocument)
        .options(
            joinedload(BidDocument.tender_requirement),
            joinedload(BidDocument.processing),
        )
        .where(BidDocument.id == new_doc.id)
    ).one()

    return _format_document_response(new_doc)


def remove_bid_document(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
) -> BidDocumentResponse:
    """Soft-removes a document from the active bid preparation."""
    profile, bid = _get_bid_for_bidder(db, current_user, bid_id)
    _validate_bid_editable(bid)

    doc = db.scalars(
        select(BidDocument)
        .options(
            joinedload(BidDocument.tender_requirement),
            joinedload(BidDocument.processing),
        )
        .where(
            and_(
                BidDocument.id == document_id,
                BidDocument.bid_id == bid.id,
                BidDocument.is_active == True,
            )
        )
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active document not found.",
        )

    doc.is_active = False
    doc.status = "REMOVED"

    db.commit()
    db.refresh(doc)

    return _format_document_response(doc)


def generate_download_access(
    db: Session,
    current_user: User,
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
) -> Tuple[BidDocument, Optional[str], bytes]:
    """
    Verifies ownership and retrieves document metadata, signed URL (if configured),
    or raw bytes for streaming.
    """
    profile, bid = _get_bid_for_bidder(db, current_user, bid_id)

    doc = db.scalars(
        select(BidDocument).where(
            and_(
                BidDocument.id == document_id,
                BidDocument.bid_id == bid.id,
            )
        )
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    signed_url = storage_service.create_signed_url(doc.storage_path, expires_in_seconds=300)
    content_bytes = storage_service.get_file_bytes(doc.storage_path)

    return doc, signed_url, content_bytes
