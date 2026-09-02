"""
Unit tests for Part 9: Bulk Verification & Batch Processing models, status transitions, and service methods.
"""

import uuid
from datetime import datetime, timezone
from app.db.models.bulk_evaluation_job import (
    BulkEvaluationJob,
    BulkEvaluationJobItem,
    BulkJobStatus,
    BulkItemStatus,
    BulkStage,
)
from app.schemas.bulk_evaluation import (
    BulkEvaluationJobCreateResponse,
    BulkEvaluationJobStatusResponse,
    BulkEvaluationSummaryCounts,
    BulkEvaluationJobItemResponse,
)


def test_bulk_job_status_constants():
    """Verify bulk job and item status constants."""
    assert BulkJobStatus.QUEUED == "QUEUED"
    assert BulkJobStatus.RUNNING == "RUNNING"
    assert BulkJobStatus.COMPLETED == "COMPLETED"
    assert BulkJobStatus.PARTIALLY_COMPLETED == "PARTIALLY_COMPLETED"
    assert BulkJobStatus.FAILED == "FAILED"
    assert BulkJobStatus.CANCELLED == "CANCELLED"

    assert BulkItemStatus.SUCCESS == "SUCCESS"
    assert BulkItemStatus.REVIEW_REQUIRED == "REVIEW_REQUIRED"
    assert BulkItemStatus.FAILED == "FAILED"
    assert BulkItemStatus.SKIPPED == "SKIPPED"


def test_bulk_stage_constants():
    """Verify processing stage progression constants."""
    expected_stages = [
        "QUEUED",
        "DOCUMENT_PROCESSING",
        "VERIFICATION",
        "COMPLIANCE",
        "SCORING",
        "RISK",
        "COMPLETED",
        "FAILED",
        "SKIPPED",
    ]
    for s in expected_stages:
        assert s in BulkStage.ALL


def test_bulk_evaluation_summary_counts_schema():
    """Verify summary counts calculations and schema serialization."""
    counts = BulkEvaluationSummaryCounts(
        total=100,
        processed=75,
        successful=60,
        failed=5,
        review_required=10,
        critical_findings=3,
        remaining=25,
        progress_percentage=75.0,
    )
    assert counts.total == 100
    assert counts.processed == 75
    assert counts.progress_percentage == 75.0
    assert counts.remaining == 25


def test_bulk_job_item_response_schema():
    """Verify job item response schema validation."""
    item_id = uuid.uuid4()
    job_id = uuid.uuid4()
    bid_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    item = BulkEvaluationJobItemResponse(
        id=item_id,
        job_id=job_id,
        bid_id=bid_id,
        bid_number="BID-001",
        bidder_name="Apex Global Ltd",
        status=BulkItemStatus.SUCCESS,
        current_stage=BulkStage.COMPLETED,
        document_processing_status="SUCCESS",
        verification_status="SUCCESS",
        compliance_status="SUCCESS",
        score_status="SUCCESS",
        risk_status="SUCCESS",
        final_score=92.5,
        risk_level="LOW",
        review_required=False,
        critical_findings_count=0,
        is_retryable=False,
        created_at=now,
    )

    assert item.final_score == 92.5
    assert item.risk_level == "LOW"
    assert item.status == "SUCCESS"
    assert item.is_retryable is False
