"""
Mock Local Content Verification Adapter for Part 5D
Provides deterministic Make-in-India (MII) local content declaration verification against synthetic fixtures.
Validates percentage, supplier class (Class-I, Class-II), product name, and certifying authority.
Does NOT decide tender compliance PASS/FAIL threshold.
"""

from typing import Any, Dict, Optional, Tuple

from app.verification.adapters.base import (
    VerificationAdapter,
    VerificationRequest,
    VerificationResult,
)
from app.verification.mock_data.mock_fixtures import MOCK_LOCAL_CONTENT_REGISTRY
from app.verification.normalizers import (
    compare_names,
    compare_percentages,
    compare_scope,
    normalize_identifier,
    normalize_percentage,
    normalize_supplier_class,
)
from app.verification.types import (
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)


class MockLocalContentAdapter(VerificationAdapter):
    """
    Deterministic Mock Local Content (MII) Verification Adapter.
    """

    @property
    def source_name(self) -> str:
        return "Mock Local Content Registry"

    @property
    def source_type(self) -> str:
        return VerificationSourceType.MOCK

    def supports(self, verification_type: str) -> bool:
        return verification_type == VerificationType.LOCAL_CONTENT

    def validate_input(self, claimed_value: Any) -> Tuple[bool, Optional[str]]:
        if claimed_value is None or str(claimed_value).strip() == "":
            return False, "Local Content claim must contain a reference number or percentage value."

        return True, None

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        if not request.claimed_value and not request.supporting_claims.get("local_content_percentage"):
            return VerificationResult(
                verification_type=VerificationType.LOCAL_CONTENT,
                verification_status=VerificationStatus.NEEDS_REVIEW,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"reason": "MISSING_VERIFICATION_VALUE"},
                error_code=VerificationErrorCode.VERIFICATION_INPUT_MISSING,
                error_message="No reference or local content percentage was provided for verification.",
            )

        ref_id = normalize_identifier(request.claimed_value) if request.claimed_value else ""
        claimed_pct = normalize_percentage(
            request.supporting_claims.get("local_content_percentage")
            or request.supporting_claims.get("percentage")
            or request.claimed_value
        )
        claimed_class = normalize_supplier_class(
            request.supporting_claims.get("supplier_class")
            or request.supporting_claims.get("class")
        )
        claimed_product = (
            request.supporting_claims.get("product_name")
            or request.supporting_claims.get("product_or_scope")
            or request.extra_context.get("product_name")
        )
        claimed_entity = (
            request.supporting_claims.get("entity_name")
            or request.supporting_claims.get("company_name")
            or request.supporting_claims.get("legal_name")
            or request.extra_context.get("bidder_name")
        )

        # Lookup by reference ID or fallback to matching mock entry
        record = MOCK_LOCAL_CONTENT_REGISTRY.get(ref_id)
        if not record and ref_id:
            # Fallback search by entity or product in registry
            for k, v in MOCK_LOCAL_CONTENT_REGISTRY.items():
                if claimed_entity and compare_names(claimed_entity, v.get("entity_name"))[0] == VerificationMatchStatus.MATCH:
                    record = v
                    break

        # 1. Simulated Source Outage
        if record and record.get("status") == "UNAVAILABLE":
            return VerificationResult(
                verification_type=VerificationType.LOCAL_CONTENT,
                verification_status=VerificationStatus.UNAVAILABLE,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=str(claimed_pct or ref_id),
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={
                    "field": "local_content",
                    "claimed_value": str(claimed_pct or ref_id),
                    "source": self.source_name,
                    "simulated_outage": True,
                },
                raw_response=record,
                error_code=record.get("error_code", VerificationErrorCode.SOURCE_UNAVAILABLE),
                error_message=record.get("error_message", "Mock Local Content Registry is currently unavailable."),
            )

        # 2. Not Found in Mock Registry
        if not record:
            return VerificationResult(
                verification_type=VerificationType.LOCAL_CONTENT,
                verification_status=VerificationStatus.NOT_VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=str(claimed_pct or ref_id),
                verified_value=None,
                match_status=VerificationMatchStatus.MISMATCH,
                confidence=1.0,
                match_summary={"reference": VerificationMatchStatus.MISMATCH},
                evidence={
                    "field": "local_content",
                    "claimed_value": str(claimed_pct or ref_id),
                    "source": self.source_name,
                    "matched": False,
                    "details": "Local Content declaration reference not found in Mock Local Content Registry records.",
                },
                raw_response={"found": False, "reference": ref_id},
                error_code=None,
                error_message="Local Content declaration was not found in Mock Registry records.",
            )

        # 3. Found in Registry: Compare Percentage, Supplier Class, and Product
        registry_pct = float(record.get("local_content_percentage", 0.0))
        registry_class = record.get("supplier_class", "CLASS_I")
        registry_product = record.get("product_name", "")
        registry_entity = record.get("entity_name", "")
        registry_status = record.get("status", "VALID")

        pct_match, pct_conf = compare_percentages(claimed_pct, registry_pct)
        class_match = VerificationMatchStatus.MATCH if claimed_class in [registry_class, "UNKNOWN"] else VerificationMatchStatus.MISMATCH
        product_match, _ = compare_scope(claimed_product, registry_product)
        entity_match, _ = compare_names(claimed_entity, registry_entity)

        match_summary: Dict[str, str] = {
            "local_content_percentage": pct_match,
            "supplier_class": class_match,
            "product_name": product_match,
            "entity_name": entity_match,
            "status": registry_status,
        }

        normalized_claim_payload: Dict[str, Any] = {
            "reference_number": ref_id,
            "local_content_percentage": claimed_pct,
            "supplier_class": claimed_class,
            "product_name": claimed_product,
            "entity_name": claimed_entity,
        }

        normalized_verified_payload: Dict[str, Any] = {
            "reference_number": record.get("reference_number", ref_id),
            "local_content_percentage": registry_pct,
            "supplier_class": registry_class,
            "product_name": registry_product,
            "entity_name": registry_entity,
            "declaration_date": record.get("declaration_date"),
            "status": registry_status,
        }

        # Determine Verification Status and Confidence
        if claimed_pct is not None and pct_match == VerificationMatchStatus.MISMATCH:
            v_status = VerificationStatus.NEEDS_REVIEW
            overall_match = VerificationMatchStatus.MISMATCH
            confidence = 0.60
            reason_msg = f"Local Content claim percentage '{claimed_pct}%' differs from registry record '{registry_pct}%'."
        elif claimed_entity and entity_match == VerificationMatchStatus.MISMATCH:
            v_status = VerificationStatus.NEEDS_REVIEW
            overall_match = VerificationMatchStatus.MISMATCH
            confidence = 0.65
            reason_msg = f"Local Content declaration entity '{claimed_entity}' differs from registry declarant '{registry_entity}'."
        else:
            v_status = VerificationStatus.VERIFIED
            overall_match = VerificationMatchStatus.MATCH if pct_match == VerificationMatchStatus.MATCH else VerificationMatchStatus.PARTIAL_MATCH
            confidence = 1.0 if pct_match == VerificationMatchStatus.MATCH else 0.90
            reason_msg = f"Local Content declaration verified against Mock MII Registry ({registry_pct}%, Class: {registry_class})."

        evidence_payload: Dict[str, Any] = {
            "field": "local_content",
            "claimed_value": f"{claimed_pct}%" if claimed_pct is not None else ref_id,
            "verified_value": f"{registry_pct}%",
            "source": self.source_name,
            "matched": v_status == VerificationStatus.VERIFIED,
            "claimed_percentage": claimed_pct,
            "verified_percentage": registry_pct,
            "supplier_class": registry_class,
            "claimed_supplier_class": claimed_class,
            "product_name": registry_product,
            "entity_name": registry_entity,
            "registration_status": registry_status,
            "declaration_date": record.get("declaration_date"),
            "reason": reason_msg,
        }

        return VerificationResult(
            verification_type=VerificationType.LOCAL_CONTENT,
            verification_status=v_status,
            source_name=self.source_name,
            source_type=self.source_type,
            claimed_value=str(claimed_pct or ref_id),
            verified_value=f"{registry_pct}%",
            match_status=overall_match,
            confidence=confidence,
            match_summary=match_summary,
            evidence=evidence_payload,
            normalized_claim_payload=normalized_claim_payload,
            normalized_verified_payload=normalized_verified_payload,
            raw_response=record,
            error_code=None,
            error_message=reason_msg if v_status == VerificationStatus.NEEDS_REVIEW else None,
        )
