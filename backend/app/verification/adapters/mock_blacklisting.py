"""
Mock Blacklisting Verification Adapter for Part 5E
Provides deterministic checking of bidder organizations against synthetic blacklisting registry fixtures.
Matches across PAN, GSTIN, CIN, Udyam, and Entity Legal Name.
Preserves registry status: 'CLEAR', 'BLACKLISTED', 'EXPIRED'.
Does NOT decide tender disqualification (evaluated in Part 6).
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from app.verification.adapters.base import (
    VerificationAdapter,
    VerificationRequest,
    VerificationResult,
)
from app.verification.mock_data.mock_fixtures import MOCK_BLACKLISTING_REGISTRY
from app.verification.normalizers import (
    compare_names,
    normalize_cin,
    normalize_identifier,
    normalize_org_name,
    normalize_udyam_number,
)
from app.verification.types import (
    VerificationErrorCode,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)


class MockBlacklistingAdapter(VerificationAdapter):
    """
    Deterministic Mock Central Blacklisting Registry Adapter.
    """

    @property
    def source_name(self) -> str:
        return "Mock Blacklisting Registry"

    @property
    def source_type(self) -> str:
        return VerificationSourceType.MOCK

    def supports(self, verification_type: str) -> bool:
        return verification_type == VerificationType.BLACKLISTING

    def validate_input(self, claimed_value: Any) -> Tuple[bool, Optional[str]]:
        if claimed_value is None or str(claimed_value).strip() == "":
            return False, "Organization identifier or name is required for blacklisting verification."
        return True, None

    async def verify(self, request: VerificationRequest) -> VerificationResult:
        supp = request.supporting_claims or {}

        # 1. Identify Candidate Matching Keys
        pan = normalize_identifier(supp.get("pan") or supp.get("pan_number") or (request.claimed_value if len(str(request.claimed_value)) == 10 else ""))
        gstin = normalize_identifier(supp.get("gstin") or (request.claimed_value if len(str(request.claimed_value)) == 15 else ""))
        cin = normalize_cin(supp.get("cin") or "")
        udyam = normalize_udyam_number(supp.get("udyam_number") or supp.get("udyam_registration_number") or "")
        entity_name = supp.get("entity_name") or supp.get("company_name") or supp.get("legal_name") or request.extra_context.get("bidder_name") or (request.claimed_value if not pan and not gstin else "")
        self_declaration = supp.get("blacklisting_declaration") or supp.get("declaration") or "NOT_BLACKLISTED"

        # Check for simulated outage
        if pan == "BL-UNAV-0000" or gstin == "BL-UNAV-0000" or request.claimed_value == "BL-UNAV-0000":
            outage_entry = MOCK_BLACKLISTING_REGISTRY["BL-UNAV-0000"]
            return VerificationResult(
                verification_type=VerificationType.BLACKLISTING,
                verification_status=VerificationStatus.UNAVAILABLE,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=request.claimed_value,
                match_status=VerificationMatchStatus.UNKNOWN,
                confidence=0.0,
                evidence={"simulated_outage": True, "source": self.source_name},
                raw_response=outage_entry,
                error_code=outage_entry.get("error_code", VerificationErrorCode.SOURCE_UNAVAILABLE),
                error_message=outage_entry.get("error_message", "Mock Blacklisting source unavailable."),
            )

        # 2. Query Mock Registry in Priority Order
        matched_record: Optional[Dict[str, Any]] = None
        match_dimension = "NONE"
        is_strong_id_match = False

        for key, rec in MOCK_BLACKLISTING_REGISTRY.items():
            if key == "BL-UNAV-0000":
                continue

            r_pan = rec.get("pan")
            r_gstin = rec.get("gstin")
            r_cin = rec.get("cin")
            r_name = rec.get("entity_name")

            if pan and r_pan and pan == r_pan:
                matched_record = rec
                match_dimension = "PAN"
                is_strong_id_match = True
                break
            elif gstin and r_gstin and gstin == r_gstin:
                matched_record = rec
                match_dimension = "GSTIN"
                is_strong_id_match = True
                break
            elif cin and r_cin and cin == r_cin:
                matched_record = rec
                match_dimension = "CIN"
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
            # Clean / Not Blacklisted
            evidence = {
                "registry_status": "CLEAR",
                "source": self.source_name,
                "searched_identifiers": {"pan": pan, "gstin": gstin, "cin": cin, "entity_name": entity_name},
                "matched": True,
                "details": "No active blacklisting record found in Mock Blacklisting Registry.",
                "self_declaration": self_declaration,
                "is_mock_source": True,
            }

            return VerificationResult(
                verification_type=VerificationType.BLACKLISTING,
                verification_status=VerificationStatus.VERIFIED,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=str(pan or gstin or entity_name or request.claimed_value),
                verified_value="CLEAR",
                match_status=VerificationMatchStatus.MATCH,
                confidence=1.0,
                match_summary={"blacklisting_status": "CLEAR", "match_dimension": "NO_RECORD_FOUND"},
                evidence=evidence,
                normalized_claim_payload={"entity_name": entity_name, "pan": pan, "gstin": gstin, "declaration": self_declaration},
                normalized_verified_payload={"registry_status": "CLEAR", "record_found": False},
                raw_response={"found": False, "status": "CLEAR"},
            )

        # 4. Record Found in Registry
        reg_status = matched_record.get("registry_status", "BLACKLISTED")
        authority = matched_record.get("authority", "Vigilance Authority")
        ref_num = matched_record.get("reference_number", "BL-RECORD")
        eff_until = matched_record.get("effective_until")

        # Check date expiry
        if eff_until:
            try:
                until_dt = datetime.strptime(eff_until, "%Y-%m-%d")
                if until_dt.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                    reg_status = "EXPIRED"
            except ValueError:
                pass

        # Partial Name Match Only -> NEEDS_REVIEW (cannot assert blacklist match on partial name alone)
        if match_dimension == "ENTITY_NAME_PARTIAL" and not is_strong_id_match:
            evidence = {
                "registry_status": reg_status,
                "source": self.source_name,
                "match_dimension": match_dimension,
                "matched_entity_name": matched_record.get("entity_name"),
                "claimed_entity_name": entity_name,
                "authority": authority,
                "reference_number": ref_num,
                "details": "Partial name match found in Blacklisting Registry without corroborating PAN/GSTIN identifier. Officer review required.",
                "is_mock_source": True,
            }
            return VerificationResult(
                verification_type=VerificationType.BLACKLISTING,
                verification_status=VerificationStatus.NEEDS_REVIEW,
                source_name=self.source_name,
                source_type=self.source_type,
                claimed_value=str(entity_name or request.claimed_value),
                verified_value=reg_status,
                match_status=VerificationMatchStatus.PARTIAL_MATCH,
                confidence=0.60,
                match_summary={"blacklisting_status": reg_status, "match_dimension": match_dimension},
                evidence=evidence,
                raw_response=matched_record,
                error_message="Potential blacklisting match on partial entity name requires manual review.",
            )

        # Corroborated Identifier Match
        is_declaration_conflict = (self_declaration.upper() in ["NOT_BLACKLISTED", "NO", "FALSE", "CLEAN"] and reg_status == "BLACKLISTED")

        evidence = {
            "registry_status": reg_status,
            "source": self.source_name,
            "match_dimension": match_dimension,
            "entity_name": matched_record.get("entity_name"),
            "pan": matched_record.get("pan"),
            "gstin": matched_record.get("gstin"),
            "cin": matched_record.get("cin"),
            "authority": authority,
            "reference_number": ref_num,
            "effective_from": matched_record.get("effective_from"),
            "effective_until": eff_until,
            "reason_summary": matched_record.get("reason_summary"),
            "declaration_conflict": is_declaration_conflict,
            "is_mock_source": True,
        }

        v_status = VerificationStatus.NEEDS_REVIEW if is_declaration_conflict else VerificationStatus.VERIFIED

        return VerificationResult(
            verification_type=VerificationType.BLACKLISTING,
            verification_status=v_status,
            source_name=self.source_name,
            source_type=self.source_type,
            claimed_value=str(pan or gstin or entity_name or request.claimed_value),
            verified_value=reg_status,
            match_status=VerificationMatchStatus.MATCH,
            confidence=1.0 if is_strong_id_match else 0.90,
            match_summary={"blacklisting_status": reg_status, "match_dimension": match_dimension, "declaration_conflict": is_declaration_conflict},
            evidence=evidence,
            normalized_claim_payload={"entity_name": entity_name, "pan": pan, "gstin": gstin, "declaration": self_declaration},
            normalized_verified_payload={"registry_status": reg_status, "authority": authority, "reference_number": ref_num, "reason": matched_record.get("reason_summary")},
            raw_response=matched_record,
            error_message="Bidder self-declaration conflicts with active blacklisting record." if is_declaration_conflict else None,
        )
