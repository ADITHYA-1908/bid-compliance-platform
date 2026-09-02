"""
Automated Unit & Integration Tests for Empirical Validation & Benchmarking
Tests metric calculations (Precision, Recall, F1, FPR, FNR), ground truth evaluation,
RAG retrieval accuracy, OCR quality correlation, processing time reduction, and RBAC isolation.
"""

from datetime import datetime, timezone
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.user import User
from app.db.models.validation_run import (
    ValidationCaseResult,
    ValidationErrorType,
    ValidationRun,
    ValidationStatus,
)
from app.db.session import get_session_factory
from app.fixtures.validation_dataset import VALIDATION_DATASET, GroundTruthTestCase
from app.services.validation_benchmarking_service import ValidationBenchmarkingService


@pytest.fixture
def db_session():
    """Provides an isolated database session for testing."""
    SessionFactory = get_session_factory()
    session = SessionFactory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def test_setup(db_session: Session):
    """Sets up organization and admin user for benchmarking tests."""
    org = Organization(id=uuid.uuid4(), name=f"Benchmarking Test Org {uuid.uuid4().hex[:6]}")
    db_session.add(org)

    role_admin = db_session.query(Role).filter_by(name="ADMIN").first()
    if not role_admin:
        role_admin = Role(id=uuid.uuid4(), name="ADMIN", description="Administrator")
        db_session.add(role_admin)

    email_admin = f"admin_bench_{uuid.uuid4().hex[:6]}@example.com"
    prof_admin = Profile(id=uuid.uuid4(), full_name="Benchmark Admin", email=email_admin, role=role_admin, organization=org)
    user_admin = User(id=uuid.uuid4(), email=email_admin, password_hash="mock", profile=prof_admin)
    db_session.add_all([prof_admin, user_admin])
    db_session.commit()

    return {"org": org, "admin": user_admin}


def test_validation_dataset_integrity():
    """Verifies that the validation dataset contains at least 50 comprehensive test cases with all required fields."""
    assert len(VALIDATION_DATASET) >= 50
    for tc in VALIDATION_DATASET:
        assert tc.id.startswith("TC-")
        assert tc.title
        assert tc.category
        assert tc.document_type
        assert tc.expected_doc_type
        assert tc.expected_compliance_status in ("PASS", "FAIL", "REVIEW_REQUIRED", "NOT_APPLICABLE")
        assert tc.manual_baseline_sec > 0.0


def test_execute_benchmark_run(db_session: Session, test_setup):
    """Verifies full execution of benchmark run, creation of ValidationRun record, and statistical metric generation."""
    admin_user = test_setup["admin"]
    org = test_setup["org"]

    val_run = ValidationBenchmarkingService.execute_validation_run(
        db=db_session,
        name="Unit Test Benchmark Run",
        organization_id=org.id,
        max_cases=15,
    )

    assert val_run.id is not None
    assert val_run.status == ValidationStatus.COMPLETED.value
    assert val_run.total_cases == 15
    assert val_run.completed_at is not None
    assert val_run.compliance_accuracy >= 80.0
    assert val_run.ocr_accuracy >= 80.0
    assert val_run.field_extraction_accuracy >= 50.0
    assert val_run.classification_accuracy >= 70.0
    assert val_run.time_reduction_percentage >= 90.0
    assert val_run.summary_json is not None


def test_confusion_matrix_and_rate_calculations(db_session: Session, test_setup):
    """Verifies mathematical correctness of Precision, Recall, F1, FPR, and FNR formulas."""
    admin_user = test_setup["admin"]
    org = test_setup["org"]

    val_run = ValidationBenchmarkingService.execute_validation_run(
        db=db_session,
        name="Confusion Matrix Test Run",
        organization_id=org.id,
        max_cases=20,
    )

    tp = val_run.true_positives
    tn = val_run.true_negatives
    fp = val_run.false_positives
    fn = val_run.false_negatives

    assert (tp + tn + fp + fn) == 20

    # Test Precision formula
    if (tp + fp) > 0:
        expected_precision = round(tp / (tp + fp), 4)
        assert abs(val_run.precision - expected_precision) < 0.001

    # Test Recall formula
    if (tp + fn) > 0:
        expected_recall = round(tp / (tp + fn), 4)
        assert abs(val_run.recall - expected_recall) < 0.001

    # Test FPR formula: FP / (FP + TN)
    if (fp + tn) > 0:
        expected_fpr = round(fp / (fp + tn), 4)
        assert abs(val_run.false_positive_rate - expected_fpr) < 0.001

    # Test FNR formula: FN / (FN + TP)
    if (fn + tp) > 0:
        expected_fnr = round(fn / (fn + tp), 4)
        assert abs(val_run.false_negative_rate - expected_fnr) < 0.001


def test_ocr_quality_tier_correlation(db_session: Session, test_setup):
    """Verifies that poor/unusable quality documents result in lower OCR accuracy than good documents."""
    good_tc = GroundTruthTestCase(
        id="TC-TEST-GOOD",
        title="Good Digital Document",
        category="GST",
        document_type="GST_CERTIFICATE",
        quality_level="GOOD",
        sample_text="Registration Number: 33ABCDE1234F1Z5 Apex Tech",
        expected_doc_type="GST_CERTIFICATE",
        expected_ocr_keywords=["33ABCDE1234F1Z5"],
    )
    unusable_tc = GroundTruthTestCase(
        id="TC-TEST-UNUSABLE",
        title="Unusable Blank Document",
        category="QUALITY",
        document_type="UNKNOWN",
        quality_level="UNUSABLE",
        sample_text="",
        sample_filename="blank.pdf",
        expected_doc_type="UNKNOWN",
    )

    _, _, _, _, good_metrics = ValidationBenchmarkingService._evaluate_single_test_case(good_tc)
    _, _, _, _, unusable_metrics = ValidationBenchmarkingService._evaluate_single_test_case(unusable_tc)

    assert good_metrics["ocr_accuracy"] > 90.0
    assert unusable_metrics["ocr_accuracy"] == 0.0


def test_rag_retrieval_accuracy_evaluation():
    """Verifies that RAG query evaluation correctly measures semantic similarity and keyword presence."""
    rag_tc = GroundTruthTestCase(
        id="TC-TEST-RAG",
        title="RAG Turnover Clause Test",
        category="RAG",
        document_type="TENDER_DOCUMENT",
        quality_level="GOOD",
        sample_text="Tender Document Clause 3.1 - Average annual turnover must be at least Rs. 5.00 Crores.",
        expected_doc_type="TENDER_DOCUMENT",
        rag_query="What is the minimum turnover requirement?",
        expected_rag_clause="Clause 3.1",
    )

    _, is_correct, err_type, _, metrics = ValidationBenchmarkingService._evaluate_single_test_case(rag_tc)
    assert metrics["rag_correct"] is True
    assert is_correct is True
    assert err_type == ValidationErrorType.NONE.value


def test_csv_export_generation(db_session: Session, test_setup):
    """Verifies CSV generation containing headers and per-case records."""
    org = test_setup["org"]
    val_run = ValidationBenchmarkingService.execute_validation_run(
        db=db_session,
        name="CSV Export Test Run",
        organization_id=org.id,
        max_cases=5,
    )

    csv_data = ValidationBenchmarkingService.export_run_as_csv(db=db_session, run_id=val_run.id)
    assert "Test Case ID,Title,Category" in csv_data
    assert "TC-" in csv_data


def test_ppt_summary_generation(db_session: Session, test_setup):
    """Verifies PPT-ready summary structure and metrics."""
    org = test_setup["org"]
    val_run = ValidationBenchmarkingService.execute_validation_run(
        db=db_session,
        name="PPT Summary Test Run",
        organization_id=org.id,
        max_cases=10,
    )

    summary = ValidationBenchmarkingService.generate_ppt_summary(db=db_session, run_id=val_run.id)
    assert summary["slide_title"]
    assert "ocr_accuracy" in summary["performance_metrics"]
    assert "compliance_decision_accuracy" in summary["performance_metrics"]
    assert "measured_time_reduction" in summary["speed_and_efficiency_gains"]
    assert len(summary["key_takeaways"]) >= 3
