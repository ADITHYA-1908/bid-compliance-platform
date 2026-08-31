"""
Mock Debarment Verification Adapter for Part 5E
Provides deterministic checking of bidder organizations against synthetic debarment registry fixtures.
Matches across CIN, PAN, GSTIN, and Entity Legal Name.
Preserves registry status: 'CLEAR', 'DEBARRED', 'EXPIRED'.
Does NOT decide tender disqualification (evaluated in Part 6).
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from app.verification.adapters.base import (
    VerificationAdapter,
    VerificationRequest,
    VerificationResult,
)
from app.verification.mock_data.mock_fixtures import MOCK_DEBARMENT_REGISTRY
from app.verification.normalizers import (
    compare_names,
    normalize_cin,
    normalize_identifier,
)
from app.verification.types import (
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)


class MockDebarmentAdapter(VerificationAdapter):
    """
    Deterministic Mock Debarment Registry Adapter.
    """

    @property
    def source_name(self) -> str:
        return "Mock Debarment Registry"

    @property
    def source_type(self) -> str:
        return VerificationSourceType.MOCK

    def supports(self, verification_type: str) -> bool:
        return verification_type == VerificationType.DEBARMENT

    def validate_input(self, claimed_value: Any) -> Tuple[bool, Optional[str]]:
        if claimed_value is None or str(claimed_value).strip() == "":
            return False, "Organization identifier or name is required for debarment verification."
        return True, None

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        supp = request.supporting_claims or {}

        # 1. Identify Candidate Matching Keys
        pan = normalize_identifier(supp.get("pan") or supp.get("pan_number") or (request.claimed_value if len(str(request.claimed_value)) == 10 else ""))
        cin = normalize_cin(supp.get("cin") or (request.claimed_value if len(str(request.claimed_value)) == 21 else ""))
        gstin = normalize_identifier(supp.get("gstin") or "")
        entity_name = supp.get("entity_name") or supp.get("company_name") or supp.get("legal_name") or request.extra_context.get("bidder_name") or (request.claimed_value if not pan and not cin else "")

        # Check for simulated outage
        if cin == "DB-UNAV-0000" or pan == "DB-UNAV-0000" or request.claimed_value == "DB-UNAV-0000":
            outage_entry = MOCK_DEBARMENT_REGISTRY["DB-UNAV-0000"]
            return VerificationResult(
                verification_type=VerificationType.DEBARMENT,
                verification_status=VerificationStatus.UNAVAILABLE,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"simulated_outage": True, "source": self.source_name},
                raw_response=outage_entry,
                error_code=outage_entry.get("error_code", VerificationErrorCode.SOURCE_UNAVAILABLE),
                error_message=outage_entry.get("error_message", "Mock Debarment source unavailable."),
            )

        # 2. Query Mock Debarment Registry
        matched_record: Optional[Dict[str, Any]] = None
        match_dimension = "NONE"
        is_strong_id_match = False

        for key, rec in MOCK_DEBARMENT_REGISTRY.items():
            if key == "DB-UNAV-0000":
                continue

            r_cin = rec.get("cin")
            r_pan = rec.get("pan")
            r_name = rec.get("entity_name")

            if cin and r_cin and cin == r_cin:
                matched_record = rec
                match_dimension = "CIN"
                is_strong_id_match = True
                break
            elif pan and r_pan and pan == r_pan:
                matched_record = rec
                match_dimension = "PAN"
                is_strong_id_match = True
                break
            elif entity_name and r_name:
                name_match, _ = compare_names(entity_name, r_name)
                if name_match == VerificationMatchStatus.MATCH:
                    matched_record = rec
                    match_dimension = "ENTITY_NAME_EXACT"
                    break
                elif name_match == VerificationMatchStatus.PARTIAL_MATCH:
                    matched_record = rec
                    match_dimension = "ENTITY_NAME_PARTIAL"
                    break

        # 3. Formulate Outcome
        if not matched_record:
            # Clean / Not Debarred
            evidence = {
                "registry_status": "CLEAR",
                "source": self.source_name,
                "searched_identifiers": {"pan": pan, "cin": cin, "entity_name": entity_name},
                "matched": True,
                "details": "No debarment record found in Mock Debarment Registry.",
                "is_mock_source": True,
            }

            return VerificationResult(
                verification_type=VerificationType.DEBARMENT,
                verification_status=VerificationStatus.VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=str(cin or pan or entity_name or request.claimed_value),
                verified_value="CLEAR",
                match_status=VerificationMatchStatus.MATCH,
                confidence=1.0,
                match_summary={"debarment_status": "CLEAR", "match_dimension": "NO_RECORD_FOUND"},
                evidence=evidence,
                normalized_claim_payload={"entity_name": entity_name, "cin": cin, "pan": pan},
                normalized_verified_payload={"registry_status": "CLEAR", "record_found": False},
                raw_response={"found": False, "status": "CLEAR"},
            )

        # 4. Record Found
        reg_status = matched_record.get("registry_status", "DEBARRED")
        authority = matched_record.get("authority", "Debarment Authority")
        ref_num = matched_record.get("reference_number", "DB-RECORD")
        eff_until = matched_record.get("effective_until")

        # Check date expiry
        if eff_until:
            try:
                until_dt = datetime.strptime(eff_until, "%Y-%m-%d")
                if until_dt.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                    reg_status = "EXPIRED"
            except ValueError:
                pass

        if match_dimension == "ENTITY_NAME_PARTIAL" and not is_strong_id_match:
            evidence = {
                "registry_status": reg_status,
                "source": self.source_name,
                "match_dimension": match_dimension,
                "matched_entity_name": matched_record.get("entity_name"),
                "claimed_entity_name": entity_name,
                "authority": authority,
                "reference_number": ref_num,
                "details": "Partial name match in Debarment Registry without corroborating identifier. Officer review required.",
                "is_mock_source": True,
            }
            return VerificationResult(
                verification_type=VerificationType.DEBARMENT,
                verification_status=VerificationStatus.NEEDS_REVIEW,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=str(entity_name or request.claimed_value),
                verified_value=reg_status,
                match_status=VerificationMatchStatus.PARTIAL_MATCH,
                confidence=0.60,
                match_summary={"debarment_status": reg_status, "match_dimension": match_dimension},
                evidence=evidence,
                raw_response=matched_record,
                error_message="Potential debarment match on partial entity name requires manual review.",
            )

        evidence = {
            "registry_status": reg_status,
            "source": self.source_name,
            "match_dimension": match_dimension,
            "entity_name": matched_record.get("entity_name"),
            "cin": matched_record.get("cin"),
            "pan": matched_record.get("pan"),
            "authority": authority,
            "reference_number": ref_num,
            "effective_from": matched_record.get("effective_from"),
            "effective_until": eff_until,
            "reason_summary": matched_record.get("reason_summary"),
            "is_mock_source": True,
        }

        return VerificationResult(
            verification_type=VerificationType.DEBARMENT,
            verification_status=VerificationStatus.VERIFIED,
            source_name=self.source_name,
            source_type=self.source_type,
            claimed_value=str(cin or pan or entity_name or request.claimed_value),
            verified_value=reg_status,
            match_status=VerificationMatchStatus.MATCH,
            confidence=1.0 if is_strong_id_match else 0.90,
            match_summary={"debarment_status": reg_status, "match_dimension": match_dimension},
            evidence=evidence,
            normalized_claim_payload={"entity_name": entity_name, "cin": cin, "pan": pan},
            normalized_verified_payload={"registry_status": reg_status, "authority": authority, "reference_number": ref_num, "reason": matched_record.get("reason_summary")},
            raw_response=matched_record,
        )
