"""
Validation and Benchmarking API Router for BidVerify AI
Admin and Procurement endpoints for triggering benchmark runs, viewing performance KPIs,
failure analysis, CSV/JSON exports, and PPT-ready presentation metrics.
"""

import math
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.authorization import require_role
from app.db.models.user import User
from app.db.session import get_db
from app.fixtures.validation_dataset import VALIDATION_DATASET
from app.schemas.validation import (
    ValidationCaseListResponse,
    ValidationCaseResultResponse,
    ValidationDatasetCaseResponse,
    ValidationPPTSummaryResponse,
    ValidationRunCreateRequest,
    ValidationRunListResponse,
    ValidationRunResponse,
)
from app.services.validation_benchmarking_service import ValidationBenchmarkingService

router = APIRouter()


@router.post(
    "/runs",
    response_model=ValidationRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger a new empirical validation and benchmark run",
)
def create_validation_run(
    payload: ValidationRunCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "PROCUREMENT_OFFICER"])),
):
    """
    Executes an empirical benchmarking run against the ground truth dataset.
    Calculates actual OCR, classification, extraction, compliance, confusion matrix,
    FPR, FNR, RAG, and processing time reduction.
    """
    org_id = current_user.profile.organization_id if current_user.profile else None
    run = ValidationBenchmarkingService.execute_validation_run(
        db=db,
        name=payload.name,
        organization_id=org_id,
        tags=payload.tags,
        max_cases=payload.max_cases,
        notes=payload.notes,
    )
    return run


@router.get(
    "/runs",
    response_model=ValidationRunListResponse,
    summary="List historical validation runs",
)
def list_validation_runs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "PROCUREMENT_OFFICER"])),
):
    """
    Retrieves paginated historical benchmark runs.
    """
    runs, total = ValidationBenchmarkingService.get_validation_runs(
        db=db,
        page=page,
        page_size=page_size,
    )
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    return {
        "items": runs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get(
    "/runs/{run_id}",
    response_model=ValidationRunResponse,
    summary="Get detailed metrics for a specific validation run",
)
def get_validation_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "PROCUREMENT_OFFICER"])),
):
    """
    Retrieves complete benchmark statistics, confusion matrix, and breakdown telemetry.
    """
    run = ValidationBenchmarkingService.get_validation_run_by_id(db=db, run_id=run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation run '{run_id}' was not found.",
        )
    return run


@router.get(
    "/runs/{run_id}/cases",
    response_model=ValidationCaseListResponse,
    summary="Get per-case evaluation results for a validation run",
)
def get_validation_case_results(
    run_id: uuid.UUID,
    category: Optional[str] = Query(None, description="Filter by category"),
    error_type: Optional[str] = Query(None, description="Filter by error type"),
    failed_only: Optional[bool] = Query(None, description="Filter only failed cases"),
    search: Optional[str] = Query(None, description="Search by case ID or title"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "PROCUREMENT_OFFICER"])),
):
    """
    Retrieves granular per-case results with ground truth vs actual outputs.
    """
    cases, total = ValidationBenchmarkingService.get_case_results_for_run(
        db=db,
        run_id=run_id,
        category=category,
        error_type=error_type,
        failed_only=failed_only,
        search=search,
        page=page,
        page_size=page_size,
    )
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    return {
        "items": cases,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get(
    "/runs/{run_id}/export",
    summary="Export validation run results as CSV or JSON",
)
def export_validation_run(
    run_id: uuid.UUID,
    format: str = Query("csv", regex="^(csv|json)$", description="Export format (csv or json)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "PROCUREMENT_OFFICER"])),
):
    """
    Exports validation case results for offline analysis and auditing.
    """
    run = ValidationBenchmarkingService.get_validation_run_by_id(db=db, run_id=run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation run '{run_id}' was not found.",
        )

    if format == "json":
        cases, _ = ValidationBenchmarkingService.get_case_results_for_run(
            db=db, run_id=run_id, page=1, page_size=500
        )
        data = {
            "validation_run": ValidationRunResponse.model_validate(run).model_dump(),
            "case_results": [ValidationCaseResultResponse.model_validate(c).model_dump() for c in cases],
        }
        return data

    csv_content = ValidationBenchmarkingService.export_run_as_csv(db=db, run_id=run_id)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=validation_run_{run_id}_{int(time.time())}.csv"
        },
    )


@router.get(
    "/runs/{run_id}/ppt-summary",
    response_model=ValidationPPTSummaryResponse,
    summary="Generate PPT-ready results summary for presentations",
)
def get_ppt_summary(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "PROCUREMENT_OFFICER"])),
):
    """
    Generates a structured, evidence-based performance summary suitable for presentations.
    """
    try:
        return ValidationBenchmarkingService.generate_ppt_summary(db=db, run_id=run_id)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.get(
    "/dataset",
    response_model=List[ValidationDatasetCaseResponse],
    summary="List ground truth test cases specification",
)
def get_validation_dataset(
    current_user: User = Depends(require_role(["ADMIN", "PROCUREMENT_OFFICER"])),
):
    """
    Lists the available ground-truth test case definitions in the validation dataset.
    """
    return [
        ValidationDatasetCaseResponse(
            id=c.id,
            title=c.title,
            category=c.category,
            document_type=c.document_type,
            quality_level=c.quality_level,
            expected_doc_type=c.expected_doc_type,
            expected_compliance_status=c.expected_compliance_status,
            manual_baseline_sec=c.manual_baseline_sec,
        )
        for c in VALIDATION_DATASET
    ]
