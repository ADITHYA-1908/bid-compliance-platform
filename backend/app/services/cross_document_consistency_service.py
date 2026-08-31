"""
Cross-Document Consistency Engine for Part 5E
BidVerify AI — Integrated Bid Compliance Verification Platform for GeM Procurement

Evaluates cross-document, cross-source, and profile data consistency across 6 dimensions:
1. PAN vs GSTIN Embedded PAN
2. Organization Legal Name Alignment across sources
3. CIN / LLPIN Alignment
4. Udyam Registration Number Alignment
5. Registered State & Address Consistency
6. Organization Entity Type Normalization & Inferred Taxpayer Type Alignment

Preserves source provenance and review requirements without mutating original records.
Does NOT calculate final compliance PASS/FAIL or final risk scores (Part 6 & Part 7).
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.document_processing import DocumentProcessing
from app.db.models.organization import Organization
from app.db.models.user import User
from app.db.models.verification_record import VerificationRecord
from app.verification.normalizers import (
    compare_addresses,
    compare_names,
    compare_strings,
    extract_pan_entity_type,
    extract_pan_from_gstin,
    normalize_cin,
    normalize_identifier,
    normalize_org_name,
    normalize_organization_type,
    normalize_udyam_number,
)
from app.verification.types import (
    VerificationClaimSource,
    VerificationMatchStatus,
    VerificationSourceType,
    VerificationStatus,
    VerificationType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Consistency Finding Schemas
# ---------------------------------------------------------------------------

class ConsistencyFinding(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_name: str = Field(..., description="Target field evaluated (e.g. pan_gstin, legal_name, cin)")
    finding_type: str = Field(..., description="Classification (e.g. PAN_GST_MATCH, NAME_MISMATCH)")
    source_a: str = Field(..., description="Origin of value A (e.g. PAN_VERIFIED, PROFILE)")
    source_b: str = Field(..., description="Origin of value B (e.g. GST_EMBEDDED, MCA_VERIFIED)")
    value_a: Optional[str] = Field(None, description="Normalized representation of value A")
    value_b: Optional[str] = Field(None, description="Normalized representation of value B")
    match_status: str = Field(..., description="MATCH, PARTIAL_MATCH, MISMATCH, NOT_APPLICABLE, UNKNOWN")
    severity_hint: str = Field(default="INFO", description="INFO, WARNING, HIGH_ATTENTION")
    requires_review: bool = Field(default=False, description="Whether manual officer attention is recommended")
    details: str = Field(default="", description="Human-readable factual explanation of the finding")


class ConsistencyReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bid_id: uuid.UUID
    verification_status: str
    overall_match_status: str
    total_checks: int
    matched_checks: int
    review_required_checks: int
    findings: List[ConsistencyFinding]
    checked_at: datetime


# ---------------------------------------------------------------------------
# Consistency Engine Implementation
# ---------------------------------------------------------------------------

class CrossDocumentConsistencyEngine:
    """
    Evaluates coherence and identity alignment across all active document extractions,
    verified registry records, and the bidder's profile.
    """

    def evaluate_bid_consistency(
        self,
        db: Session,
        bid: Bid,
    ) -> Tuple[str, str, List[ConsistencyFinding], Dict[str, Any]]:
        """
        Executes all 6 consistency dimensions for a bid.
        Returns:
            (verification_status, overall_match_status, list_of_findings, evidence_dict)
        """
        org: Optional[Organization] = bid.bidder_organization

        # 1. Fetch all active verification records for this bid
        v_records = db.scalars(
            select(VerificationRecord).where(
                VerificationRecord.bid_id == bid.id,
                VerificationRecord.is_active == True,
            )
        ).all()

        v_map: Dict[str, VerificationRecord] = {}
        for r in v_records:
            if r.verification_type not in v_map:
                v_map[r.verification_type] = r

        # 2. Fetch all active document extractions
        docs = db.scalars(
            select(BidDocument).where(
                BidDocument.bid_id == bid.id,
                BidDocument.is_active == True,
            )
        ).all()

        extracted_fields_by_doc: Dict[str, Dict[str, Any]] = {}
        for doc in docs:
            proc: Optional[DocumentProcessing] = doc.processing
            if proc and proc.extracted_data and isinstance(proc.extracted_data, dict):
                fields = proc.extracted_data.get("fields", {})
                clean_fields = {}
                for k, v in fields.items():
                    if isinstance(v, dict) and "value" in v:
                        clean_fields[k] = v["value"]
                    else:
                        clean_fields[k] = v
                extracted_fields_by_doc[doc.document_type] = clean_fields

        findings: List[ConsistencyFinding] = []

        # =====================================================================
        # Dimension 1: PAN vs GSTIN Embedded PAN
        # =====================================================================
        pan_sources: List[Tuple[str, str]] = []
        gstin_sources: List[Tuple[str, str]] = []

        # PAN sources
        if VerificationType.PAN in v_map and v_map[VerificationType.PAN].verified_value:
            pan_sources.append(("PAN_VERIFIED", v_map[VerificationType.PAN].verified_value))
        elif "PAN" in extracted_fields_by_doc and extracted_fields_by_doc["PAN"].get("pan_number"):
            pan_sources.append(("PAN_DOCUMENT", extracted_fields_by_doc["PAN"]["pan_number"]))
        elif org and org.pan_number:
            pan_sources.append(("PROFILE_PAN", org.pan_number))

        # GSTIN sources
        if VerificationType.GST in v_map and v_map[VerificationType.GST].verified_value:
            gstin_sources.append(("GST_VERIFIED", v_map[VerificationType.GST].verified_value))
        elif "GST_CERTIFICATE" in extracted_fields_by_doc and extracted_fields_by_doc["GST_CERTIFICATE"].get("gstin"):
            gstin_sources.append(("GST_DOCUMENT", extracted_fields_by_doc["GST_CERTIFICATE"]["gstin"]))
        elif org and org.gstin:
            gstin_sources.append(("PROFILE_GSTIN", org.gstin))

        if pan_sources and gstin_sources:
            src_pan_name, raw_pan = pan_sources[0]
            src_gst_name, raw_gstin = gstin_sources[0]

            clean_pan = normalize_identifier(raw_pan)
            embedded_pan = extract_pan_from_gstin(raw_gstin)

            if embedded_pan:
                if clean_pan == embedded_pan:
                    findings.append(
                        ConsistencyFinding(
                            field_name="pan_gstin",
                            finding_type="PAN_GST_MATCH",
                            source_a=src_pan_name,
                            source_b=f"{src_gst_name}_EMBEDDED",
                            value_a=clean_pan,
                            value_b=embedded_pan,
                            match_status=VerificationMatchStatus.MATCH,
                            severity_hint="INFO",
                            requires_review=False,
                            details=f"Standalone PAN '{clean_pan}' matches the embedded PAN within GSTIN '{raw_gstin}'.",
                        )
                    )
                else:
                    findings.append(
                        ConsistencyFinding(
                            field_name="pan_gstin",
                            finding_type="PAN_GST_MISMATCH",
                            source_a=src_pan_name,
                            source_b=f"{src_gst_name}_EMBEDDED",
                            value_a=clean_pan,
                            value_b=embedded_pan,
                            match_status=VerificationMatchStatus.MISMATCH,
                            severity_hint="HIGH_ATTENTION",
                            requires_review=True,
                            details=f"Standalone PAN '{clean_pan}' ({src_pan_name}) does NOT match embedded PAN '{embedded_pan}' in GSTIN '{raw_gstin}' ({src_gst_name}).",
                        )
                    )
            else:
                findings.append(
                    ConsistencyFinding(
                        field_name="pan_gstin",
                        finding_type="GSTIN_PARSING_FAILED",
                        source_a=src_pan_name,
                        source_b=src_gst_name,
                        value_a=clean_pan,
                        value_b=raw_gstin,
                        match_status=VerificationMatchStatus.UNKNOWN,
                        severity_hint="WARNING",
                        requires_review=True,
                        details=f"Could not extract embedded 10-character PAN from GSTIN '{raw_gstin}'.",
                    )
                )
        else:
            findings.append(
                ConsistencyFinding(
                    field_name="pan_gstin",
                    finding_type="PAN_GST_INSUFFICIENT_DATA",
                    source_a=pan_sources[0][0] if pan_sources else "MISSING",
                    source_b=gstin_sources[0][0] if gstin_sources else "MISSING",
                    value_a=pan_sources[0][1] if pan_sources else None,
                    value_b=gstin_sources[0][1] if gstin_sources else None,
                    match_status=VerificationMatchStatus.NOT_APPLICABLE,
                    severity_hint="INFO",
                    requires_review=False,
                    details="Either PAN or GSTIN is not available for embedded cross-verification.",
                )
            )

        # =====================================================================
        # Dimension 2: Organization / Legal Name Consistency
        # =====================================================================
        name_sources: List[Tuple[str, str]] = []
        if org and org.name:
            name_sources.append(("PROFILE_ORGANIZATION", org.name))

        # Check verified registries for entity names
        for v_type in [
            VerificationType.GST,
            VerificationType.PAN,
            VerificationType.UDYAM,
            VerificationType.MCA,
            VerificationType.STARTUP_INDIA,
            VerificationType.NSIC,
            VerificationType.EPFO,
            VerificationType.ESIC,
        ]:
            if v_type in v_map and v_map[v_type].evidence:
                ev = v_map[v_type].evidence
                v_name = (
                    ev.get("legal_name")
                    or ev.get("name")
                    or ev.get("entity_name")
                    or ev.get("company_name")
                    or ev.get("enterprise_name")
                    or ev.get("establishment_name")
                    or ev.get("employer_name")
                )
                if v_name:
                    name_sources.append((f"{v_type}_VERIFIED", v_name))

        if len(name_sources) >= 2:
            primary_src, primary_name = name_sources[0]
            for other_src, other_name in name_sources[1:]:
                m_status, _ = compare_names(primary_name, other_name)
                is_mismatch = (m_status == VerificationMatchStatus.MISMATCH)

                findings.append(
                    ConsistencyFinding(
                        field_name="legal_name",
                        finding_type="ORGANIZATION_NAME_MATCH" if not is_mismatch else "ORGANIZATION_NAME_MISMATCH",
                        source_a=primary_src,
                        source_b=other_src,
                        value_a=primary_name,
                        value_b=other_name,
                        match_status=m_status,
                        severity_hint="HIGH_ATTENTION" if is_mismatch else "INFO",
                        requires_review=is_mismatch,
                        details=(
                            f"Organization name matches between {primary_src} and {other_src}."
                            if not is_mismatch
                            else f"Organization name differs: '{primary_name}' ({primary_src}) vs '{other_name}' ({other_src})."
                        ),
                    )
                )

        # =====================================================================
        # Dimension 3: CIN / LLPIN Consistency
        # =====================================================================
        cin_sources: List[Tuple[str, str]] = []
        if VerificationType.MCA in v_map and v_map[VerificationType.MCA].verified_value:
            cin_sources.append(("MCA_VERIFIED", v_map[VerificationType.MCA].verified_value))
        if "COMMERCIAL_DOCUMENT" in extracted_fields_by_doc and extracted_fields_by_doc["COMMERCIAL_DOCUMENT"].get("cin"):
            cin_sources.append(("COMMERCIAL_DOC", extracted_fields_by_doc["COMMERCIAL_DOCUMENT"]["cin"]))

        if len(cin_sources) >= 2:
            c1_src, c1_val = cin_sources[0]
            c2_src, c2_val = cin_sources[1]
            n_c1 = normalize_cin(c1_val)
            n_c2 = normalize_cin(c2_val)

            if n_c1 == n_c2:
                findings.append(
                    ConsistencyFinding(
                        field_name="cin",
                        finding_type="CIN_MATCH",
                        source_a=c1_src,
                        source_b=c2_src,
                        value_a=n_c1,
                        value_b=n_c2,
                        match_status=VerificationMatchStatus.MATCH,
                        severity_hint="INFO",
                        requires_review=False,
                        details=f"CIN/LLPIN '{n_c1}' is consistent across {c1_src} and {c2_src}.",
                    )
                )
            else:
                findings.append(
                    ConsistencyFinding(
                        field_name="cin",
                        finding_type="CIN_MISMATCH",
                        source_a=c1_src,
                        source_b=c2_src,
                        value_a=n_c1,
                        value_b=n_c2,
                        match_status=VerificationMatchStatus.MISMATCH,
                        severity_hint="HIGH_ATTENTION",
                        requires_review=True,
                        details=f"CIN/LLPIN mismatch: '{n_c1}' ({c1_src}) vs '{n_c2}' ({c2_src}).",
                    )
                )

        # =====================================================================
        # Dimension 4: Udyam Registration Consistency
        # =====================================================================
        udyam_sources: List[Tuple[str, str]] = []
        if VerificationType.UDYAM in v_map and v_map[VerificationType.UDYAM].verified_value:
            udyam_sources.append(("UDYAM_VERIFIED", v_map[VerificationType.UDYAM].verified_value))
        if "UDYAM_CERTIFICATE" in extracted_fields_by_doc and extracted_fields_by_doc["UDYAM_CERTIFICATE"].get("udyam_registration_number"):
            udyam_sources.append(("UDYAM_DOC", extracted_fields_by_doc["UDYAM_CERTIFICATE"]["udyam_registration_number"]))

        if len(udyam_sources) >= 2:
            u1_src, u1_val = udyam_sources[0]
            u2_src, u2_val = udyam_sources[1]
            n_u1 = normalize_udyam_number(u1_val)
            n_u2 = normalize_udyam_number(u2_val)

            if n_u1 == n_u2:
                findings.append(
                    ConsistencyFinding(
                        field_name="udyam_number",
                        finding_type="UDYAM_MATCH",
                        source_a=u1_src,
                        source_b=u2_src,
                        value_a=n_u1,
                        value_b=n_u2,
                        match_status=VerificationMatchStatus.MATCH,
                        severity_hint="INFO",
                        requires_review=False,
                        details=f"Udyam registration number '{n_u1}' is consistent across {u1_src} and {u2_src}.",
                    )
                )
            else:
                findings.append(
                    ConsistencyFinding(
                        field_name="udyam_number",
                        finding_type="UDYAM_MISMATCH",
                        source_a=u1_src,
                        source_b=u2_src,
                        value_a=n_u1,
                        value_b=n_u2,
                        match_status=VerificationMatchStatus.MISMATCH,
                        severity_hint="HIGH_ATTENTION",
                        requires_review=True,
                        details=f"Udyam number mismatch: '{n_u1}' ({u1_src}) vs '{n_u2}' ({u2_src}).",
                    )
                )

        # =====================================================================
        # Dimension 5: Registered State & Address Consistency
        # =====================================================================
        state_sources: List[Tuple[str, str]] = []
        if org and org.state:
            state_sources.append(("PROFILE_STATE", org.state))
        if VerificationType.GST in v_map and v_map[VerificationType.GST].evidence:
            gst_state = v_map[VerificationType.GST].evidence.get("state")
            if gst_state:
                state_sources.append(("GST_VERIFIED", gst_state))
        if VerificationType.MCA in v_map and v_map[VerificationType.MCA].evidence:
            mca_state = v_map[VerificationType.MCA].evidence.get("registered_office_state")
            if mca_state:
                state_sources.append(("MCA_VERIFIED", mca_state))

        if len(state_sources) >= 2:
            st1_src, st1_val = state_sources[0]
            st2_src, st2_val = state_sources[1]
            st_match, _ = compare_strings(st1_val, st2_val)
            is_st_mismatch = (st_match == VerificationMatchStatus.MISMATCH)

            findings.append(
                ConsistencyFinding(
                    field_name="registered_state",
                    finding_type="STATE_MATCH" if not is_st_mismatch else "STATE_MISMATCH",
                    source_a=st1_src,
                    source_b=st2_src,
                    value_a=st1_val,
                    value_b=st2_val,
                    match_status=st_match,
                    severity_hint="WARNING" if is_st_mismatch else "INFO",
                    requires_review=is_st_mismatch,
                    details=(
                        f"State is consistent ('{st1_val}') between {st1_src} and {st2_src}."
                        if not is_st_mismatch
                        else f"Registered state differs: '{st1_val}' ({st1_src}) vs '{st2_val}' ({st2_src})."
                    ),
                )
            )

        # Address comparison
        addr_sources: List[Tuple[str, str]] = []
        org_addr = getattr(org, "registered_address", None) or getattr(org, "address", None)
        if org and org_addr:
            addr_sources.append(("PROFILE_ADDRESS", org_addr))
        if VerificationType.GST in v_map and v_map[VerificationType.GST].evidence:
            gst_addr = v_map[VerificationType.GST].evidence.get("address")
            if gst_addr:
                addr_sources.append(("GST_VERIFIED", gst_addr))
        if VerificationType.MCA in v_map and v_map[VerificationType.MCA].evidence:
            mca_addr = v_map[VerificationType.MCA].evidence.get("registered_office_address")
            if mca_addr:
                addr_sources.append(("MCA_VERIFIED", mca_addr))

        if len(addr_sources) >= 2:
            ad1_src, ad1_val = addr_sources[0]
            ad2_src, ad2_val = addr_sources[1]
            ad_match, ad_conf = compare_addresses(ad1_val, ad2_val)
            is_ad_mismatch = (ad_match == VerificationMatchStatus.MISMATCH)

            findings.append(
                ConsistencyFinding(
                    field_name="registered_address",
                    finding_type="ADDRESS_MATCH" if not is_ad_mismatch else "ADDRESS_MISMATCH",
                    source_a=ad1_src,
                    source_b=ad2_src,
                    value_a=ad1_val,
                    value_b=ad2_val,
                    match_status=ad_match,
                    severity_hint="WARNING" if is_ad_mismatch else "INFO",
                    requires_review=is_ad_mismatch,
                    details=(
                        f"Registered office address aligned across {ad1_src} and {ad2_src}."
                        if not is_ad_mismatch
                        else f"Registered office address token mismatch between {ad1_src} and {ad2_src}."
                    ),
                )
            )

        # =====================================================================
        # Dimension 6: Organization Legal Entity Type Normalization
        # =====================================================================
        type_sources: List[Tuple[str, str]] = []
        if VerificationType.MCA in v_map and v_map[VerificationType.MCA].evidence:
            mca_type = v_map[VerificationType.MCA].evidence.get("company_type")
            if mca_type:
                type_sources.append(("MCA_VERIFIED", normalize_organization_type(mca_type)))
        if VerificationType.UDYAM in v_map and v_map[VerificationType.UDYAM].evidence:
            udyam_type = v_map[VerificationType.UDYAM].evidence.get("organization_type")
            if udyam_type:
                type_sources.append(("UDYAM_VERIFIED", normalize_organization_type(udyam_type)))
        if pan_sources:
            pan_meta = extract_pan_entity_type(pan_sources[0][1])
            if pan_meta.get("entity_type_description"):
                type_sources.append(("PAN_INFERRED", normalize_organization_type(pan_meta["entity_type_description"])))

        if len(type_sources) >= 2:
            t1_src, t1_val = type_sources[0]
            t2_src, t2_val = type_sources[1]
            if t1_val in [t2_val, "OTHER", "UNKNOWN"] or t2_val in ["OTHER", "UNKNOWN"]:
                t_match = VerificationMatchStatus.MATCH
            else:
                t_match = VerificationMatchStatus.MISMATCH

            is_t_mismatch = (t_match == VerificationMatchStatus.MISMATCH)
            findings.append(
                ConsistencyFinding(
                    field_name="organization_type",
                    finding_type="ORGANIZATION_TYPE_MATCH" if not is_t_mismatch else "ORGANIZATION_TYPE_MISMATCH",
                    source_a=t1_src,
                    source_b=t2_src,
                    value_a=t1_val,
                    value_b=t2_val,
                    match_status=t_match,
                    severity_hint="WARNING" if is_t_mismatch else "INFO",
                    requires_review=is_t_mismatch,
                    details=(
                        f"Canonical organization type ('{t1_val}') matches across {t1_src} and {t2_src}."
                        if not is_t_mismatch
                        else f"Legal entity type divergence: '{t1_val}' ({t1_src}) vs '{t2_val}' ({t2_src})."
                    ),
                )
            )

        # =====================================================================
        # Aggregate Outcome Formulation
        # =====================================================================
        total_checks = len(findings)
        matched_checks = sum(1 for f in findings if f.match_status in [VerificationMatchStatus.MATCH, VerificationMatchStatus.PARTIAL_MATCH])
        review_required_checks = sum(1 for f in findings if f.requires_review)

        if review_required_checks > 0:
            v_status = VerificationStatus.NEEDS_REVIEW
            overall_match = VerificationMatchStatus.MISMATCH
        elif total_checks > 0 and matched_checks == total_checks:
            v_status = VerificationStatus.VERIFIED
            overall_match = VerificationMatchStatus.MATCH
        elif total_checks == 0 or (total_checks == 1 and findings[0].match_status == VerificationMatchStatus.NOT_APPLICABLE):
            v_status = VerificationStatus.NEEDS_REVIEW
            overall_match = VerificationMatchStatus.UNKNOWN
        else:
            v_status = VerificationStatus.VERIFIED
            overall_match = VerificationMatchStatus.PARTIAL_MATCH

        evidence_dict = {
            "total_checks": total_checks,
            "matched_checks": matched_checks,
            "review_required_checks": review_required_checks,
            "findings": [f.model_dump() for f in findings],
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "source": "Cross-Document Consistency Engine",
            "is_internal_engine": True,
        }

        return v_status, overall_match, findings, evidence_dict


consistency_engine = CrossDocumentConsistencyEngine()
