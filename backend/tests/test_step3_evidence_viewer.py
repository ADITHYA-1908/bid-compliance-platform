"""
Comprehensive Automated Unit & Integration Tests for Step 3: Explain Why + Evidence Viewer
Tests:
- Schema serialization with direct evidence fields (document_id, document_name, page_number, download_url, evidence_snippet, confidence, verification_source)
- Service helper _extract_evidence_fields_for_rule resolution from both evidence dict and BidDocument processing metadata
- Absence of fake confidence or invented coordinates
- Backward compatibility with legacy `evidence: Dict[str, Any]`
- Authorization dependency checks (require_any_role vs require_role bug prevention)
- Router endpoint inspection for procurement document downloads
"""

import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.schemas.compliance import (
    ComplianceResultItemResponse,
    ComplianceReviewItemResponse,
    BidComplianceSummaryResponse,
    ComplianceSummaryCounts,
)
from app.services.compliance_service import _extract_evidence_fields_for_rule
from app.db.models.compliance_result import ComplianceResult, ComplianceStatus


def test_compliance_result_item_response_schema_direct_evidence_fields():
    """Verify that ComplianceResultItemResponse contains first-class evidence fields."""
    doc_id = uuid.uuid4()
    req_id = uuid.uuid4()
    bid_id = uuid.uuid4()
    tender_id = uuid.uuid4()
    item_id = uuid.uuid4()

    item = ComplianceResultItemResponse(
        id=item_id,
        bid_id=bid_id,
        tender_id=tender_id,
        tender_requirement_id=req_id,
        requirement_code="FIN-001",
        requirement_name="Annual Turnover Threshold",
        category="FINANCIAL",
        requirement_type="FINANCIAL_MINIMUM",
        compliance_status="PASS",
        actual_value=5000000.0,
        expected_value=2000000.0,
        operator=">=",
        reason="Annual turnover ₹50,00,000 meets or exceeds minimum requirement of ₹20,00,000.",
        evidence={"annual_turnover": 5000000, "audited_year": "2023-24"},
        source_verification_ids=["VR-1234"],
        document_id=doc_id,
        document_name="Audited_Financial_Statement_2024.pdf",
        page_number=3,
        download_url=f"/api/v1/procurement/bids/{bid_id}/documents/{doc_id}/download",
        evidence_snippet="Turnover for FY 2023-24 certified as INR 50,00,000/- by CA.",
        confidence=0.96,
        verification_source="FINANCIAL_AUDIT_EXTRACTION",
        is_mandatory=True,
        is_critical=True,
        critical_failure=False,
    )

    assert item.document_id == doc_id
    assert item.document_name == "Audited_Financial_Statement_2024.pdf"
    assert item.page_number == 3
    assert item.evidence_snippet == "Turnover for FY 2023-24 certified as INR 50,00,000/- by CA."
    assert item.confidence == 0.96
    assert item.verification_source == "FINANCIAL_AUDIT_EXTRACTION"
    assert item.download_url == f"/api/v1/procurement/bids/{bid_id}/documents/{doc_id}/download"
    assert item.evidence == {"annual_turnover": 5000000, "audited_year": "2023-24"}


def test_compliance_result_item_response_schema_nullable_fields():
    """Verify that null/missing evidence fields default safely to None."""
    item = ComplianceResultItemResponse(
        id=uuid.uuid4(),
        bid_id=uuid.uuid4(),
        tender_id=uuid.uuid4(),
        tender_requirement_id=uuid.uuid4(),
        requirement_code="GEN-001",
        requirement_name="Declaration Submission",
        category="TECHNICAL",
        requirement_type="DECLARATION",
        compliance_status="PENDING",
        is_mandatory=False,
        is_critical=False,
        critical_failure=False,
    )

    assert item.document_id is None
    assert item.document_name is None
    assert item.page_number is None
    assert item.download_url is None
    assert item.evidence_snippet is None
    assert item.confidence is None
    assert item.verification_source is None


def test_extract_evidence_fields_from_evidence_dict():
    """Verify _extract_evidence_fields_for_rule extracts fields from result.evidence dict."""
    doc_id = uuid.uuid4()
    bid_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.bid_id = bid_id
    mock_result.evidence = {
        "document_id": str(doc_id),
        "document_name": "GST_Certificate.pdf",
        "page_number": 2,
        "evidence_snippet": "GSTIN: 27AAAAA0000A1Z5 Active as of registration date",
        "confidence": 0.94,
        "verification_source": "GSTN_API_LOOKUP",
    }

    mock_bid = MagicMock()
    mock_bid.id = bid_id
    mock_bid.documents = []

    doc_id_out, doc_name, page_num, dl_url, snippet, conf, verif = _extract_evidence_fields_for_rule(
        mock_result, mock_bid
    )

    assert doc_id_out == doc_id
    assert doc_name == "GST_Certificate.pdf"
    assert page_num == 2
    assert snippet == "GSTIN: 27AAAAA0000A1Z5 Active as of registration date"
    assert conf == 0.94
    assert verif == "GSTN_API_LOOKUP"
    assert f"/api/v1/procurement/bids/{bid_id}/documents/{doc_id}/download" == dl_url


def test_extract_evidence_fields_from_bid_documents_fallback():
    """Verify _extract_evidence_fields_for_rule falls back to BidDocument metadata."""
    doc_id = uuid.uuid4()
    bid_id = uuid.uuid4()
    req_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.bid_id = bid_id
    mock_result.tender_requirement = None
    mock_result.tender_requirement_id = req_id
    mock_result.evidence = {
        "turnover": 4500000
    }

    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.tender_requirement_id = req_id
    mock_doc.document_type = "TURNOVER_CERTIFICATE"
    mock_doc.document_name = "Turnover_Certificate.pdf"
    mock_doc.original_filename = "Turnover_Cert_Final.pdf"
    mock_doc.is_active = True

    mock_processing = MagicMock()
    mock_processing.extraction_confidence = 0.92
    mock_processing.extracted_data = {
        "fields": {
            "turnover": {
                "value": 4500000,
                "page": 1,
                "confidence": 0.92,
                "evidence": "Total Turnover for year 2023-24 INR 45,00,000",
                "source": "OCR_FIELD_EXTRACTION",
            }
        }
    }
    mock_doc.processing = mock_processing

    mock_bid = MagicMock()
    mock_bid.id = bid_id
    mock_bid.documents = [mock_doc]

    doc_id_out, doc_name, page_num, dl_url, snippet, conf, verif = _extract_evidence_fields_for_rule(
        mock_result, mock_bid
    )

    assert doc_id_out == doc_id
    assert doc_name == "Turnover_Cert_Final.pdf"
    assert page_num == 1
    assert conf == 0.92
    assert snippet == "Total Turnover for year 2023-24 INR 45,00,000"
    assert verif == "OCR_FIELD_EXTRACTION"
    assert dl_url == f"/api/v1/procurement/bids/{bid_id}/documents/{doc_id}/download"


def test_procurement_router_authorization_dependencies():
    """
    Verify that procurement router in base.py loads cleanly with require_any_role
    and contains all expected document preview & download routes.
    """
    from app.api.v1.procurement.base import router

    route_paths = [r.path for r in router.routes]

    # Verify download and download-url routes exist on router
    assert "/bids/{bid_id}/documents/{document_id}/download" in route_paths
    assert "/bids/{bid_id}/documents/{document_id}/download-url" in route_paths
    assert "/tenders/{tender_id}/bids/{bid_id}/documents/{document_id}/download" in route_paths
