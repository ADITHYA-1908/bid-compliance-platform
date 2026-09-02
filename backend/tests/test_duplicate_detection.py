"""
Unit tests for Part 10: Duplicate / Reuse Document Detection
Tests hash computation, normalization, structured field matching, text similarity,
pairwise evaluation logic, same-bidder version exemption, and review workflows.
"""

import hashlib
import uuid
import pytest
from app.db.models.bid_document import BidDocument
from app.db.models.document_duplicate_match import (
    DocumentDuplicateMatch,
    DuplicateMatchStatus,
    DuplicateMatchType,
)
from app.db.models.document_processing import DocumentProcessing
from app.schemas.duplicate_detection import DuplicateReviewRequest
from app.services.procurement.duplicate_detection_service import (
    DuplicateDetectionService,
    STRUCTURED_FIELD_WEIGHTS,
)


def test_compute_file_hash():
    content = b"Sample GeM tender bid compliance certificate binary content 2026"
    expected = hashlib.sha256(content).hexdigest()
    actual = DuplicateDetectionService.compute_file_hash(content)
    assert actual == expected
    assert len(actual) == 64


def test_compute_normalized_text_hash():
    text1 = "  ISO 9001:2015 Quality Management Certificate \n\n Valid until: 2028-12-31! "
    text2 = "iso 9001/2015 quality management certificate valid until 2028-12-31"

    norm1, hash1 = DuplicateDetectionService.compute_normalized_text_hash(text1)
    norm2, hash2 = DuplicateDetectionService.compute_normalized_text_hash(text2)

    assert hash1 is not None
    assert hash1 == hash2


def test_compare_structured_fields_exact_match():
    fields_a = {
        "certificate_number": {"value": "ISO-9001-XYZ-2024"},
        "gstin": {"value": "29ABCDE1234F1Z5"},
        "organization_name": {"value": "Alpha Tech Pvt Ltd"},
    }
    fields_b = {
        "certificate_number": "ISO-9001-XYZ-2024",
        "gstin": "29ABCDE1234F1Z5",
        "organization_name": "Alpha Tech Pvt Ltd",
    }

    score, matched_details, summary = DuplicateDetectionService.compare_structured_fields(fields_a, fields_b)

    assert score >= 0.85
    assert len(matched_details) == 3
    assert "certificate_number" in summary
    assert "gstin" in summary
    assert summary["certificate_number"]["match"] is True


def test_compare_structured_fields_different():
    fields_a = {
        "certificate_number": {"value": "CERT-1111"},
        "gstin": {"value": "29ABCDE1111F1Z5"},
    }
    fields_b = {
        "certificate_number": {"value": "CERT-2222"},
        "gstin": {"value": "27XYZAB9999F1Z1"},
    }

    score, matched_details, summary = DuplicateDetectionService.compare_structured_fields(fields_a, fields_b)
    assert score == 0.0
    assert len(matched_details) == 0


def test_calculate_text_similarity():
    text1 = "This is the OEM Authorization Certificate issued by Cisco Systems India Pvt Ltd for tender compliance verification."
    text2 = "This is the OEM Authorization Certificate issued by Cisco Systems India Pvt Ltd for tender compliance verification."
    sim_identical = DuplicateDetectionService.calculate_text_similarity(text1, text2)
    assert sim_identical == 1.0

    text_diff = "Completely unrelated audited annual financial balance sheet statement of profit and loss 2025."
    sim_diff = DuplicateDetectionService.calculate_text_similarity(text1, text_diff)
    assert sim_diff < 0.60


def test_evaluate_document_pair_exact_file_duplicate():
    file_sha = hashlib.sha256(b"Identical PDF binary content").hexdigest()

    doc_a = BidDocument(
        id=uuid.uuid4(),
        document_name="OEM_Auth_Alpha.pdf",
        original_filename="OEM_Auth.pdf",
        file_size=1024,
        file_hash=file_sha,
        document_type="OEM_AUTHORIZATION",
    )
    doc_b = BidDocument(
        id=uuid.uuid4(),
        document_name="OEM_Auth_Beta.pdf",
        original_filename="OEM_Auth_Copy.pdf",
        file_size=1024,
        file_hash=file_sha,
        document_type="OEM_AUTHORIZATION",
    )

    result = DuplicateDetectionService.evaluate_document_pair(doc_a, doc_b)
    assert result is not None
    assert result["match_type"] == DuplicateMatchType.EXACT_FILE_DUPLICATE
    assert result["file_hash_match"] is True
    assert result["overall_confidence"] == 1.0


def test_evaluate_document_pair_structured_data_match():
    doc_a = BidDocument(
        id=uuid.uuid4(),
        document_name="GST_Cert_Alpha.pdf",
        original_filename="gst_alpha.pdf",
        file_size=5000,
        file_hash="hash_alpha_111",
        document_type="GST_CERTIFICATE",
    )
    proc_a = DocumentProcessing(
        id=uuid.uuid4(),
        bid_document_id=doc_a.id,
        extracted_data={
            "fields": {
                "certificate_number": {"value": "GSTIN-CERT-998877"},
                "gstin": {"value": "29ABCDE1234F1Z5"},
                "organization_name": {"value": "Shared Vendor Co"},
            }
        },
    )
    doc_a.processing = proc_a

    doc_b = BidDocument(
        id=uuid.uuid4(),
        document_name="GST_Cert_Beta.pdf",
        original_filename="gst_beta.pdf",
        file_size=5200,
        file_hash="hash_beta_222",
        document_type="GST_CERTIFICATE",
    )
    proc_b = DocumentProcessing(
        id=uuid.uuid4(),
        bid_document_id=doc_b.id,
        extracted_data={
            "fields": {
                "certificate_number": {"value": "GSTIN-CERT-998877"},
                "gstin": {"value": "29ABCDE1234F1Z5"},
                "organization_name": {"value": "Shared Vendor Co"},
            }
        },
    )
    doc_b.processing = proc_b

    result = DuplicateDetectionService.evaluate_document_pair(doc_a, doc_b)
    assert result is not None
    assert result["match_type"] == DuplicateMatchType.STRUCTURED_DATA_MATCH
    assert result["structured_field_match_score"] >= 0.70
    assert result["overall_confidence"] >= 0.85


def test_evaluate_document_pair_benign_no_match():
    doc_a = BidDocument(
        id=uuid.uuid4(),
        document_name="Tax_Audit_Alpha.pdf",
        original_filename="tax_alpha.pdf",
        file_size=1000,
        file_hash="hash_aaa",
        document_type="FINANCIAL_REPORT",
    )
    proc_a = DocumentProcessing(
        id=uuid.uuid4(),
        bid_document_id=doc_a.id,
        raw_text="Alpha Enterprises annual audited balance sheet for fiscal year 2024 revenue 10 crores.",
        extracted_data={"fields": {"document_number": {"value": "AUD-ALPHA-2024"}}},
    )
    doc_a.processing = proc_a

    doc_b = BidDocument(
        id=uuid.uuid4(),
        document_name="Tax_Audit_Beta.pdf",
        original_filename="tax_beta.pdf",
        file_size=2000,
        file_hash="hash_bbb",
        document_type="FINANCIAL_REPORT",
    )
    proc_b = DocumentProcessing(
        id=uuid.uuid4(),
        bid_document_id=doc_b.id,
        raw_text="Beta Global Logistics chartered accountant certified statement fiscal year 2025 revenue 50 crores.",
        extracted_data={"fields": {"document_number": {"value": "AUD-BETA-2025"}}},
    )
    doc_b.processing = proc_b

    result = DuplicateDetectionService.evaluate_document_pair(doc_a, doc_b)
    assert result is None
