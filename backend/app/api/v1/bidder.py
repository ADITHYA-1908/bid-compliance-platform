import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.authorization import require_role
from app.db.session import get_db
from app.db.models.user import User
from app.schemas.bidder_profile import (
    BidderProfileResponse,
    BidderOrganizationResponse,
    BidderProfileUpdate,
    BidderOrganizationUpdate,
)
from app.schemas.bidder_tender import (
    BidderTenderDetail,
    BidderTenderListResponse,
)
from app.schemas.bid import (
    BidCreate,
    BidUpdate,
    BidListItem,
    BidListResponse,
    BidResponse,
)
from app.schemas.bid_document import (
    BidDocumentResponse,
    BidDocumentListResponse,
    BidDocumentDownloadResponse,
)
from app.schemas.bid_submission import (
    BidSubmissionReadinessResponse,
    BidSubmitPayload,
    BidSubmitResponse,
)
from app.schemas.document_processing import (
    DocumentProcessingResponse,
    DocumentProcessTriggerResponse,
    DocumentExtractedTextResponse,
    DocumentClassificationResponse,
    DocumentExtractedDataResponse,
)
from app.schemas.document_quality import (
    DocumentQualityResponse,
    QualityCheckTriggerResponse,
)
from app.schemas.verification import (
    BidVerificationListResponse,
    DocumentVerificationListResponse,
    VerificationRetryResponse,
    VerificationTriggerResponse,
)
from app.schemas.compliance import BidComplianceSummaryResponse
from app.schemas.scoring import BidScoringFoundationResponse
from app.schemas.risk import BidRiskAssessmentResponse
from app.services.bidder_profile_service import (
    get_bidder_profile,
    update_bidder_profile,
    get_bidder_organization,
    update_bidder_organization,
)
from app.services.bidder_tender_service import (
    get_available_tenders,
    get_bidder_tender_detail,
)
from app.services.bid_service import (
    create_bid,
    list_bidder_bids,
    get_bid_detail,
    update_draft_bid,
    get_existing_bid_for_tender,
)
from app.services.bid_document_service import (
    upload_bid_document,
    list_bid_documents,
    get_bid_document,
    replace_bid_document,
    remove_bid_document,
    generate_download_access,
)
from app.services.bid_submission_service import (
    check_submission_readiness,
    submit_bid,
)
from app.services.document_processing_service import (
    get_document_processing,
    queue_document_processing,
    retry_document_processing,
    get_document_extracted_text,
    get_document_classification,
    get_document_extracted_data,
)
from app.services.document_quality_service import DocumentQualityService
from app.services.verification_service import (
    get_bid_consistency_report,
    get_bid_verifications,
    get_document_verifications,
    retry_verification_record,
    verify_bid_blacklisting,
    verify_bid_consistency,
    verify_document_claims,
)
from app.services.compliance_service import (
    evaluate_bid_compliance,
    get_bid_compliance,
)
from app.services.scoring_service import (
    calculate_and_save_bid_score,
    get_bid_score,
)
from app.services.risk_service import (
    calculate_and_save_bid_risk,
    get_bid_risk,
)



router = APIRouter()




@router.get("/test", summary="Bidder authorization test endpoint")
def bidder_test(
    current_user: User = Depends(require_role("BIDDER")),
):
    """
    Role-protected endpoint accessible only to authenticated BIDDER users.
    """
    return {
        "message": "Bidder access granted",
        "role": "BIDDER",
        "user_email": current_user.email,
        "organization": (
            current_user.profile.organization.name
            if current_user.profile and current_user.profile.organization
            else None
        ),
    }


# =========================================================================
# Part 3A: Bidder Profile & Organization Setup Endpoints
# =========================================================================

@router.get(
    "/profile",
    response_model=BidderProfileResponse,
    summary="Get current bidder profile and completion summary",
)
def read_bidder_profile(
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint for BIDDER to retrieve their signatory contact profile,
    linked organization summary, and real-time profile completion score.
    """
    return get_bidder_profile(db=db, current_user=current_user)


@router.patch(
    "/profile",
    response_model=BidderProfileResponse,
    summary="Update current bidder personal and signatory profile",
)
def patch_bidder_profile(
    data: BidderProfileUpdate,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint for BIDDER to update contact name, phone, or designation.
    """
    return update_bidder_profile(db=db, current_user=current_user, data=data)


@router.get(
    "/organization",
    response_model=BidderOrganizationResponse,
    summary="Get current bidder organization details and statutory registrations",
)
def read_bidder_organization(
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint for BIDDER to retrieve full business entity and registration details.
    """
    return get_bidder_organization(db=db, current_user=current_user)


@router.patch(
    "/organization",
    response_model=BidderOrganizationResponse,
    summary="Update current bidder organization details and registrations",
)
def patch_bidder_organization(
    data: BidderOrganizationUpdate,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint for BIDDER to update legal business information, registered address,
    and statutory identifiers (PAN, GSTIN, Udyam, etc.) with format and conflict validations.
    """
    return update_bidder_organization(db=db, current_user=current_user, data=data)


# =========================================================================
# Part 3B: Bidder Tender Discovery Endpoints (Read-Only)
# =========================================================================

@router.get(
    "/tenders",
    response_model=BidderTenderListResponse,
    summary="Discover and search available procurement tenders",
)
def list_available_tenders(
    search: Optional[str] = Query(None, description="Search keyword across title, tender number, department, category"),
    category: Optional[str] = Query(None, description="Filter by procurement category (e.g. IT & Telecom, Civil Works)"),
    procurement_type: Optional[str] = Query(None, description="Filter by procurement type (e.g. Goods, Services, Works)"),
    status: Optional[str] = Query(None, description="Filter by status (OPEN or PUBLISHED)"),
    sort_by: Optional[str] = Query("newest", description="Sort option: newest, deadline, value_high, value_low"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(12, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected read-only discovery endpoint for BIDDER users to browse and search
    publicly open procurement opportunities across all procuring entities.
    DRAFT and ARCHIVED tenders are strictly omitted.
    """
    return get_available_tenders(
        db=db,
        search=search,
        category=category,
        procurement_type=procurement_type,
        status_filter=status,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/tenders/{tender_id}",
    response_model=BidderTenderDetail,
    summary="Get bidder-safe detailed tender view and eligibility rules",
)
def read_available_tender_detail(
    tender_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected read-only endpoint for BIDDER users to view full tender details
    and categorized eligibility requirements formatted in human-readable terms.
    Returns 404 if the tender is in DRAFT or ARCHIVED status.
    """
    return get_bidder_tender_detail(db=db, tender_id=tender_id)


# =========================================================================
# Part 3C: Bid Creation & Tender Participation Endpoints
# =========================================================================

@router.post(
    "/tenders/{tender_id}/bids",
    response_model=BidResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft bid participation record for an OPEN tender",
)
def create_bid_for_tender(
    tender_id: uuid.UUID,
    data: Optional[BidCreate] = None,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint for BIDDER to initiate participation in an OPEN tender.
    Validates profile completion, tender status (OPEN), server deadline,
    and prevents duplicate bids by the same bidder organization (409 Conflict).
    """
    return create_bid(
        db=db,
        current_user=current_user,
        tender_id=tender_id,
        data=data,
    )


@router.get(
    "/tenders/{tender_id}/bid",
    response_model=Optional[BidListItem],
    summary="Check if current bidder organization already has a bid for a tender",
)
def check_existing_tender_bid(
    tender_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint to query if the current bidder already has an active bid
    for a specific tender. Used by the tender details UI to display 'Continue Bid'
    instead of 'Start Bid'.
    """
    return get_existing_bid_for_tender(
        db=db,
        current_user=current_user,
        tender_id=tender_id,
    )


@router.get(
    "/bids",
    response_model=BidListResponse,
    summary="List all bids belonging to the authenticated bidder organization",
)
def list_my_bids(
    search: Optional[str] = Query(None, description="Search keyword across bid number, tender title, tender number"),
    status: Optional[str] = Query(None, description="Filter by bid status (e.g. DRAFT, SUBMITTED)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint to retrieve paginated bids created by the authenticated bidder's organization.
    Cross-bidder data is strictly isolated.
    """
    return list_bidder_bids(
        db=db,
        current_user=current_user,
        search=search,
        status_filter=status,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/bids/{bid_id}",
    response_model=BidResponse,
    summary="Get full bid workspace details by bid ID",
)
def read_bid_workspace(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint to retrieve full details of a bid workspace.
    Returns 404 if the bid does not exist or belongs to another bidder organization.
    """
    return get_bid_detail(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )


@router.patch(
    "/bids/{bid_id}",
    response_model=BidResponse,
    summary="Update commercial and technical details of a DRAFT bid",
)
def patch_draft_bid(
    bid_id: uuid.UUID,
    data: BidUpdate,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint to update editable fields (quoted_amount, currency, technical_summary,
    commercial_notes, remarks) of a DRAFT bid.
    Rejects modification if the bid is not in DRAFT status.
    """
    return update_draft_bid(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        data=data,
    )


# =========================================================================
# Part 3D: Bid Document Upload & Management Endpoints
# =========================================================================

@router.post(
    "/bids/{bid_id}/documents",
    response_model=BidDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload compliance document for a draft bid",
)
def upload_document(
    bid_id: uuid.UUID,
    file: UploadFile = File(..., description="Document file binary (PDF, PNG, JPG, DOCX, XLSX)"),
    document_type: str = Form(..., description="Document type identifier (e.g. GST_CERTIFICATE, PAN, OEM_AUTHORIZATION)"),
    tender_requirement_id: Optional[uuid.UUID] = Form(None, description="Optional target tender requirement UUID"),
    notes: Optional[str] = Form(None, description="Optional remarks or notes about the document"),
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected multipart upload endpoint for BIDDER to upload statutory, technical, or commercial
    compliance proof documents against a draft bid.
    Enforces file safety, size limits, deadline validation, and replaces existing active versions.
    """
    return upload_bid_document(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        file=file,
        document_type=document_type,
        tender_requirement_id=tender_requirement_id,
        notes=notes,
    )


@router.get(
    "/bids/{bid_id}/documents",
    response_model=BidDocumentListResponse,
    summary="List all uploaded documents and readiness summary for a bid",
)
def list_documents(
    bid_id: uuid.UUID,
    include_inactive: bool = Query(False, description="Whether to include superseded/removed versions"),
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint to list all documents uploaded for the bidder's draft bid
    along with calculated progress against mandatory tender requirements.
    """
    return list_bid_documents(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        include_inactive=include_inactive,
    )


@router.get(
    "/bids/{bid_id}/documents/{document_id}",
    response_model=BidDocumentResponse,
    summary="Get document details and signed view access",
)
def read_document_detail(
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint to retrieve metadata and time-limited signed access for an uploaded document.
    """
    return get_bid_document(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
    )


@router.get(
    "/bids/{bid_id}/documents/{document_id}/download",
    summary="Securely download or view uploaded document binary",
)
def download_document_binary(
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected binary streaming endpoint for BIDDER to download or view their uploaded file.
    Streams directly with correct MIME type and content-disposition header.
    """
    doc, signed_url, content_bytes = generate_download_access(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
    )

    headers = {
        "Content-Disposition": f'inline; filename="{doc.original_filename}"',
    }
    return Response(
        content=content_bytes,
        media_type=doc.mime_type,
        headers=headers,
    )


@router.get(
    "/bids/{bid_id}/documents/{document_id}/download-url",
    response_model=BidDocumentDownloadResponse,
    summary="Get short-lived signed download URL for document",
)
def get_document_download_url(
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint returning signed download URL metadata for direct client access.
    """
    doc, signed_url, _ = generate_download_access(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
    )
    return BidDocumentDownloadResponse(
        document_id=doc.id,
        filename=doc.original_filename,
        mime_type=doc.mime_type,
        download_url=signed_url,
        expires_in_seconds=300,
    )


@router.put(
    "/bids/{bid_id}/documents/{document_id}",
    response_model=BidDocumentResponse,
    summary="Replace an active uploaded document with a new version",
)
def replace_document(
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    file: UploadFile = File(..., description="Replacement document file binary"),
    notes: Optional[str] = Form(None, description="Optional updated notes"),
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint to replace an uploaded document with a new revision.
    Marks prior active version as REPLACED and creates an incremented version record.
    """
    return replace_bid_document(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
        file=file,
        notes=notes,
    )


@router.delete(
    "/bids/{bid_id}/documents/{document_id}",
    response_model=BidDocumentResponse,
    summary="Soft-remove an uploaded document from active bid",
)
def remove_document(
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint to remove an uploaded document from active bid package.
    Marks document as is_active=False and status=REMOVED without deleting audit record.
    """
    return remove_bid_document(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
    )


# =========================================================================
# Part 3E: Bid Review & Final Submission Endpoints
# =========================================================================

@router.get(
    "/bids/{bid_id}/readiness",
    response_model=BidSubmissionReadinessResponse,
    summary="Evaluate submission readiness and mandatory checklist items",
)
def get_bid_readiness(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint to evaluate whether a draft bid proposal satisfies all pre-submission criteria:
    - Bidder profile 100% completeness
    - Commercial & technical details completeness
    - All mandatory tender compliance documents uploaded
    - Tender remains in OPEN status
    - Server-side submission deadline has not elapsed
    """
    return check_submission_readiness(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )


@router.post(
    "/bids/{bid_id}/submit",
    response_model=BidSubmitResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit final bid proposal and lock from further mutations",
)
def submit_final_bid(
    bid_id: uuid.UUID,
    payload: BidSubmitPayload,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint to execute final atomic submission of a DRAFT bid proposal.
    Enforces statutory readiness, declaration certification, sets SUBMITTED status with
    timestamp and audit reference, and locks all details and documents from subsequent editing.
    """
    return submit_bid(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        payload=payload,
    )


# =========================================================================
# Part 4A: Document Ingestion & Processing Foundation Endpoints
# =========================================================================

@router.get(
    "/bids/{bid_id}/documents/{document_id}/processing",
    response_model=DocumentProcessingResponse,
    summary="Get document processing telemetry and extraction status",
)
def read_document_processing_status(
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint for BIDDER to inspect the current processing status, stage,
    and telemetry of an uploaded bid document.
    """
    return get_document_processing(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
    )


@router.post(
    "/bids/{bid_id}/documents/{document_id}/process",
    response_model=DocumentProcessTriggerResponse,
    summary="Initialize or queue document processing pipeline",
)
def trigger_document_processing(
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint to initialize or queue document processing foundation.
    Verifies storage binary presence and sets stage to INGESTION in status QUEUED.
    """
    proc = queue_document_processing(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
    )
    return DocumentProcessTriggerResponse(
        message="Document processing queued successfully.",
        processing=proc,
    )


@router.post(
    "/bids/{bid_id}/documents/{document_id}/retry",
    response_model=DocumentProcessTriggerResponse,
    summary="Retry a failed document processing job",
)
def retry_failed_document_processing(
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint to retry processing for a FAILED document.
    Resets status to QUEUED, stage to INGESTION, clears previous errors,
    and runs PDF extraction pipeline.
    """
    proc = retry_document_processing(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
    )
    return DocumentProcessTriggerResponse(
        message="Document processing retried successfully.",
        processing=proc,
    )


@router.get(
    "/bids/{bid_id}/documents/{document_id}/extracted-text",
    response_model=DocumentExtractedTextResponse,
    summary="Get extracted text and quality telemetry for document",
)
def read_document_extracted_text(
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint for BIDDER to review extracted text, page count,
    and technical extraction telemetry.
    Strict tenant isolation enforced.
    """
    return get_document_extracted_text(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
    )


@router.get(
    "/bids/{bid_id}/documents/{document_id}/classification",
    response_model=DocumentClassificationResponse,
    summary="Get document classification results and explainability metrics",
)
def read_document_classification(
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint for BIDDER to review deterministic classification results,
    expected vs detected document class, confidence level, and explainability signals.
    Strict tenant isolation enforced.
    """
    return get_document_classification(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
    )


@router.get(
    "/bids/{bid_id}/documents/{document_id}/extracted-data",
    response_model=DocumentExtractedDataResponse,
    summary="Get structured extracted entity fields, confidence, evidence, and provenance",
)
def read_document_extracted_data(
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint for authenticated BIDDER to inspect structured entity fields,
    field-level confidence, evidence snippets, page provenance, and review flags.
    Strict tenant isolation enforced.
    """
    return get_document_extracted_data(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
    )


# =============================================================================
# Part 11: Document Quality Diagnostics Endpoints
# =============================================================================

@router.get(
    "/bids/{bid_id}/documents/{document_id}/quality",
    response_model=DocumentQualityResponse,
    summary="Get document quality check result and page-level diagnostics",
)
def read_document_quality(
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint for authenticated BIDDER to inspect image & document quality diagnostics:
    deterministic quality score (0-100), quality level (GOOD/ACCEPTABLE/POOR/UNUSABLE),
    blur sharpness, blank page detection, low resolution, skew angles, and actionable bidder feedback.
    Strict tenant isolation enforced.
    """
    return DocumentQualityService.get_document_quality_for_bidder(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
    )


@router.post(
    "/bids/{bid_id}/documents/{document_id}/quality-check",
    response_model=DocumentQualityResponse,
    summary="Trigger on-demand document quality check evaluation",
)
def trigger_document_quality_check(
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Triggers explicit pre-flight document quality evaluation before OCR/classification.
    """
    return DocumentQualityService.get_document_quality_for_bidder(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
    )


# =============================================================================
# Part 5A: Verification Engine Endpoints
# =============================================================================

@router.post(
    "/bids/{bid_id}/documents/{document_id}/verify",
    response_model=VerificationTriggerResponse,
    summary="Trigger claim verification for structured entities extracted from a document",
)
async def trigger_document_verification(
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Triggers claim verification (Mock / Development) for all verifiable structured entities
    extracted from the specified active document.
    Enforces tenant isolation and idempotency.
    """
    return await verify_document_claims(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
    )


@router.get(
    "/bids/{bid_id}/documents/{document_id}/verifications",
    response_model=DocumentVerificationListResponse,
    summary="Get claim verification records and evidence for a specific document",
)
def read_document_verifications(
    bid_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Retrieves all verification telemetry, match statuses, confidence, and concise evidence
    associated with the specified document.
    """
    return get_document_verifications(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        document_id=document_id,
    )


@router.get(
    "/bids/{bid_id}/verifications",
    response_model=BidVerificationListResponse,
    summary="Get aggregated claim verification summary and items for all bid documents",
)
def read_bid_verifications(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Aggregates verification records across all active documents in the bid package.
    Provides verification status counters for downstream evaluation.
    """
    return get_bid_verifications(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )


@router.post(
    "/bids/{bid_id}/verifications/{verification_id}/retry",
    response_model=VerificationRetryResponse,
    summary="Retry an UNAVAILABLE or FAILED verification record",
)
async def retry_verification(
    bid_id: uuid.UUID,
    verification_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Retries an individual claim verification attempt that previously resulted in
    UNAVAILABLE or FAILED status. Increments attempt counter and logs telemetry.
    """
    return await retry_verification_record(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
        verification_id=verification_id,
    )


# =============================================================================
# Part 5E: Blacklisting & Cross-Document Consistency Endpoints
# =============================================================================

@router.post(
    "/bids/{bid_id}/verify-blacklisting",
    response_model=VerificationTriggerResponse,
    summary="Trigger organization-level Blacklisting and Debarment verification",
)
async def trigger_bid_blacklisting_verification(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint to query mock blacklisting and debarment registries using
    verified organization identifiers (PAN, GSTIN, CIN, legal name).
    """
    return await verify_bid_blacklisting(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )


@router.post(
    "/bids/{bid_id}/verify-consistency",
    response_model=VerificationTriggerResponse,
    summary="Trigger cross-document and cross-source identity consistency check",
)
async def trigger_bid_consistency_verification(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint to evaluate identity coherence across PAN, GSTIN, legal name,
    CIN, Udyam, state, address, and organization type.
    """
    return await verify_bid_consistency(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )


@router.get(
    "/bids/{bid_id}/consistency",
    summary="Get cross-document identity consistency report and findings list",
)
def read_bid_consistency_report(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint to review detailed cross-document consistency findings,
    provenance, and review requirements.
    """
    return get_bid_consistency_report(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )


# =========================================================================
# Part 6A: Compliance Evaluation Engine Endpoints
# =========================================================================

@router.post(
    "/bids/{bid_id}/compliance/evaluate",
    response_model=BidComplianceSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger rule-by-rule compliance evaluation for bid requirements",
)
def trigger_bid_compliance_evaluation(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint to evaluate all active TenderRequirements against
    verified bidder data and evidence. Persists results and returns summary.
    """
    return evaluate_bid_compliance(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )


@router.get(
    "/bids/{bid_id}/compliance",
    response_model=BidComplianceSummaryResponse,
    summary="Get current compliance evaluation results and rule determinations",
)
def read_bid_compliance_results(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint to fetch current active compliance results for a bid.
    """
    return get_bid_compliance(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )


# =============================================================================
# Part 7A: Scoring Engine Foundation Endpoints
# =============================================================================

@router.get(
    "/bids/{bid_id}/score",
    response_model=BidScoringFoundationResponse,
    summary="Get scoring foundation snapshot for a bidder proposal",
)
def read_bid_score(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint for BIDDER to view the deterministic scoring foundation snapshot.
    Enforces tenant isolation.
    """
    return get_bid_score(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )


@router.post(
    "/bids/{bid_id}/score/calculate",
    response_model=BidScoringFoundationResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger scoring calculation and save new snapshot",
)
def trigger_bid_score_calculation(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint for BIDDER to trigger scoring calculation and persist a new snapshot.
    Enforces tenant isolation.
    """
    return calculate_and_save_bid_score(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )


# =============================================================================
# Part 7C: Deterministic Risk Assessment Endpoints
# =============================================================================

@router.get(
    "/bids/{bid_id}/risk",
    response_model=BidRiskAssessmentResponse,
    summary="Get base risk assessment snapshot for a bidder proposal",
)
def read_bid_risk(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint for BIDDER to view the deterministic base risk assessment snapshot.
    Enforces tenant isolation.
    """
    return get_bid_risk(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )


@router.post(
    "/bids/{bid_id}/risk/calculate",
    response_model=BidRiskAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger base risk calculation and save new snapshot",
)
def trigger_bid_risk_calculation(
    bid_id: uuid.UUID,
    current_user: User = Depends(require_role("BIDDER")),
    db: Session = Depends(get_db),
):
    """
    Protected endpoint for BIDDER to trigger deterministic base risk calculation and persist a new snapshot.
    Enforces tenant isolation.
    """
    return calculate_and_save_bid_risk(
        db=db,
        current_user=current_user,
        bid_id=bid_id,
    )








