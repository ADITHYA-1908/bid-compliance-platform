"""
Organization Identity Verification & Duplicate Entity Detection Engine
BidVerify AI — Integrated Bid Compliance Verification Platform for GeM Procurement

Provides deterministic multi-dimensional legal identity evaluation, embedded PAN in GSTIN validation,
cross-document name and address coherence, and duplicate organization profile detection.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models.audit_event import (
    AuditActorSource,
    AuditEvent,
    AuditEntityType,
    AuditEventType,
)
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.document_processing import DocumentProcessing
from app.db.models.organization import Organization
from app.db.models.organization_identity import (
    IdentityMatchStatus,
    OrganizationDuplicateMatch,
    OrganizationDuplicateMatchStatus,
    OrganizationDuplicateMatchType,
    OrganizationIdentityAssessment,
    OrganizationIdentityStatus,
)
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
    VerificationMatchStatus,
    VerificationStatus,
    VerificationType,
)

logger = logging.getLogger(__name__)


class OrganizationIdentityService:
    """
    Central service for deterministic organization identity evaluation and duplicate entity discovery.
    """

    def evaluate_organization_identity(
        self,
        db: Session,
        organization_id: uuid.UUID,
        bid_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None,
        actor_name: Optional[str] = "System Identity Engine",
    ) -> OrganizationIdentityAssessment:
        """
        Evaluates cross-document, profile, and registry identity coherence for a single organization.
        """
        org = db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise ValueError(f"Organization {organization_id} not found.")

        # 1. Gather Profile Identifiers
        claimed_pan = normalize_identifier(org.pan_number) if org.pan_number else ""
        claimed_gstin = normalize_identifier(org.gstin) if org.gstin else ""
        claimed_cin = normalize_cin(org.cin_llpin) if org.cin_llpin else ""
        claimed_udyam = normalize_udyam_number(org.udyam_number) if org.udyam_number else ""
        claimed_name = org.name or ""
        claimed_address = org.registered_address or ""

        # 2. Gather Document Extractions & Verified Records
        # Query active bid documents / extractions if bid_id provided or for organization's recent bid
        extracted_names: List[Tuple[str, str, Optional[int]]] = []  # (source, name, page)
        extracted_pans: List[Tuple[str, str]] = []  # (source, pan)
        extracted_gstins: List[Tuple[str, str]] = []  # (source, gstin)
        extracted_addresses: List[Tuple[str, str]] = []  # (source, address)
        evidence_dict: Dict[str, Any] = {}
        signals: List[Dict[str, Any]] = []

        # Check verification records
        vr_records = (
            db.query(VerificationRecord)
            .join(Bid, VerificationRecord.bid_id == Bid.id)
            .filter(Bid.bidder_organization_id == organization_id)
            .all()
        )
        verified_pan: Optional[str] = None
        verified_gstin: Optional[str] = None
        verified_cin: Optional[str] = None
        verified_udyam: Optional[str] = None
        verified_legal_name: Optional[str] = None

        for vr in vr_records:
            if vr.verification_type == VerificationType.PAN and vr.status == VerificationStatus.VERIFIED:
                verified_pan = normalize_identifier(vr.claimed_value)
                if vr.details and isinstance(vr.details, dict) and vr.details.get("registered_name"):
                    extracted_names.append(("PAN Registry", vr.details["registered_name"], 1))
            elif vr.verification_type == VerificationType.GSTIN and vr.status == VerificationStatus.VERIFIED:
                verified_gstin = normalize_identifier(vr.claimed_value)
                if vr.details and isinstance(vr.details, dict) and vr.details.get("legal_name"):
                    extracted_names.append(("GSTIN Registry", vr.details["legal_name"], 1))
            elif vr.verification_type == VerificationType.CIN and vr.status == VerificationStatus.VERIFIED:
                verified_cin = normalize_cin(vr.claimed_value)
                if vr.details and isinstance(vr.details, dict) and vr.details.get("company_name"):
                    extracted_names.append(("MCA Registry", vr.details["company_name"], 1))
            elif vr.verification_type == VerificationType.UDYAM and vr.status == VerificationStatus.VERIFIED:
                verified_udyam = normalize_udyam_number(vr.claimed_value)

        # Query DocumentProcessing structured extractions for uploaded documents
        doc_processings = (
            db.query(DocumentProcessing)
            .join(BidDocument, DocumentProcessing.bid_document_id == BidDocument.id)
            .join(Bid, BidDocument.bid_id == Bid.id)
            .filter(Bid.bidder_organization_id == organization_id)
            .all()
        )

        for dp in doc_processings:
            fields = dp.extracted_fields or {}
            doc_type = dp.classified_doc_type or "DOCUMENT"

            if "pan" in fields or "pan_number" in fields:
                p_val = normalize_identifier(fields.get("pan") or fields.get("pan_number"))
                if p_val:
                    extracted_pans.append((doc_type, p_val))
            if "gstin" in fields or "gst_number" in fields:
                g_val = normalize_identifier(fields.get("gstin") or fields.get("gst_number"))
                if g_val:
                    extracted_gstins.append((doc_type, g_val))
            if "legal_name" in fields or "company_name" in fields or "entity_name" in fields:
                n_val = fields.get("legal_name") or fields.get("company_name") or fields.get("entity_name")
                if n_val:
                    extracted_names.append((doc_type, str(n_val), 1))
            if "registered_address" in fields or "address" in fields:
                a_val = fields.get("registered_address") or fields.get("address")
                if a_val:
                    extracted_addresses.append((doc_type, str(a_val)))

        # 3. Evaluate Embedded PAN in GSTIN
        effective_pan = claimed_pan or (extracted_pans[0][1] if extracted_pans else "") or (verified_pan or "")
        effective_gstin = claimed_gstin or (extracted_gstins[0][1] if extracted_gstins else "") or (verified_gstin or "")
        embedded_pan = extract_pan_from_gstin(effective_gstin)

        pan_gst_status = IdentityMatchStatus.NOT_APPLICABLE
        if effective_pan and effective_gstin:
            if embedded_pan:
                if effective_pan == embedded_pan:
                    pan_gst_status = IdentityMatchStatus.MATCH
                    signals.append({
                        "signal": "PAN_GSTIN_EMBEDDED_MATCH",
                        "severity": "INFO",
                        "message": f"Standalone PAN ({effective_pan}) perfectly matches embedded PAN ({embedded_pan}) in GSTIN ({effective_gstin}).",
                    })
                else:
                    pan_gst_status = IdentityMatchStatus.MISMATCH
                    signals.append({
                        "signal": "PAN_GSTIN_EMBEDDED_MISMATCH",
                        "severity": "CRITICAL",
                        "message": f"Standalone PAN ({effective_pan}) conflicts with embedded PAN ({embedded_pan}) inside GSTIN ({effective_gstin}).",
                    })
            else:
                pan_gst_status = IdentityMatchStatus.UNKNOWN
        evidence_dict["pan_gst_comparison"] = {
            "claimed_pan": effective_pan or None,
            "claimed_gstin": effective_gstin or None,
            "embedded_pan_in_gstin": embedded_pan or None,
            "status": pan_gst_status,
        }

        # 4. Evaluate Legal Name Consistency across sources
        legal_name_status = IdentityMatchStatus.UNKNOWN
        name_comparisons = []
        has_name_mismatch = False

        if claimed_name and extracted_names:
            for src, ext_name, page in extracted_names:
                m_stat, conf = compare_names(claimed_name, ext_name)
                name_comparisons.append({
                    "source": src,
                    "extracted_name": ext_name,
                    "claimed_name": claimed_name,
                    "status": m_stat,
                    "confidence": conf,
                })
                if m_stat == VerificationMatchStatus.MISMATCH:
                    has_name_mismatch = True

            if has_name_mismatch:
                legal_name_status = IdentityMatchStatus.MISMATCH
                signals.append({
                    "signal": "LEGAL_NAME_INCONSISTENCY",
                    "severity": "WARNING",
                    "message": "Statutory documents display conflicting legal company names.",
                })
            else:
                legal_name_status = IdentityMatchStatus.MATCH
                signals.append({
                    "signal": "LEGAL_NAME_CONSISTENT",
                    "severity": "INFO",
                    "message": f"Organization legal name is consistent across all uploaded statutory documents ({claimed_name}).",
                })
        elif claimed_name:
            legal_name_status = IdentityMatchStatus.MATCH

        evidence_dict["legal_name"] = {
            "profile_name": claimed_name,
            "normalized_profile_name": normalize_org_name(claimed_name),
            "status": legal_name_status,
            "comparisons": name_comparisons,
        }

        # 5. Evaluate PAN Status
        pan_status = IdentityMatchStatus.NOT_APPLICABLE
        if effective_pan:
            if len(effective_pan) == 10:
                pan_status = IdentityMatchStatus.MATCH if verified_pan else IdentityMatchStatus.PARTIAL_MATCH
                pan_meta = extract_pan_entity_type(effective_pan)
                evidence_dict["pan"] = {
                    "pan": effective_pan,
                    "entity_type_inferred": pan_meta.get("entity_type_description"),
                    "status": pan_status,
                    "verified": bool(verified_pan),
                }
            else:
                pan_status = IdentityMatchStatus.MISMATCH

        # 6. Evaluate GSTIN Status
        gst_status = IdentityMatchStatus.NOT_APPLICABLE
        if effective_gstin:
            if len(effective_gstin) == 15 and (pan_gst_status != IdentityMatchStatus.MISMATCH):
                gst_status = IdentityMatchStatus.MATCH if verified_gstin else IdentityMatchStatus.PARTIAL_MATCH
            elif pan_gst_status == IdentityMatchStatus.MISMATCH:
                gst_status = IdentityMatchStatus.MISMATCH
            evidence_dict["gstin"] = {
                "gstin": effective_gstin,
                "status": gst_status,
                "verified": bool(verified_gstin),
            }

        # 7. Evaluate CIN Status
        cin_status = IdentityMatchStatus.NOT_APPLICABLE
        if claimed_cin or verified_cin:
            c_val = claimed_cin or verified_cin
            cin_status = IdentityMatchStatus.MATCH if (len(c_val) == 21 or verified_cin) else IdentityMatchStatus.PARTIAL_MATCH
            evidence_dict["cin"] = {
                "cin": c_val,
                "status": cin_status,
                "verified": bool(verified_cin),
            }

        # 8. Evaluate Udyam Status
        udyam_status = IdentityMatchStatus.NOT_APPLICABLE
        if claimed_udyam or verified_udyam:
            u_val = claimed_udyam or verified_udyam
            udyam_status = IdentityMatchStatus.MATCH if verified_udyam else IdentityMatchStatus.PARTIAL_MATCH
            evidence_dict["udyam"] = {
                "udyam_number": u_val,
                "status": udyam_status,
                "verified": bool(verified_udyam),
            }

        # 9. Evaluate Address Consistency
        address_status = IdentityMatchStatus.UNKNOWN
        if claimed_address and extracted_addresses:
            for src, ext_addr in extracted_addresses:
                a_stat, a_conf = compare_addresses(claimed_address, ext_addr)
                if a_stat == VerificationMatchStatus.MATCH:
                    address_status = IdentityMatchStatus.MATCH
                    break
                elif a_stat == VerificationMatchStatus.PARTIAL_MATCH and address_status != IdentityMatchStatus.MATCH:
                    address_status = IdentityMatchStatus.PARTIAL_MATCH
                elif a_stat == VerificationMatchStatus.MISMATCH and address_status == IdentityMatchStatus.UNKNOWN:
                    address_status = IdentityMatchStatus.MISMATCH
        elif claimed_address:
            address_status = IdentityMatchStatus.PARTIAL_MATCH

        evidence_dict["address"] = {
            "registered_address": claimed_address,
            "city": org.city,
            "state": org.state,
            "pincode": org.pincode,
            "status": address_status,
        }

        # 10. Calculate Deterministic Identity Confidence Score (0-100)
        score = 50.0  # baseline

        if pan_status == IdentityMatchStatus.MATCH:
            score += 15.0
        elif pan_status == IdentityMatchStatus.PARTIAL_MATCH:
            score += 10.0

        if gst_status == IdentityMatchStatus.MATCH:
            score += 15.0
        elif gst_status == IdentityMatchStatus.PARTIAL_MATCH:
            score += 10.0

        if pan_gst_status == IdentityMatchStatus.MATCH:
            score += 15.0
        elif pan_gst_status == IdentityMatchStatus.MISMATCH:
            score -= 35.0

        if legal_name_status == IdentityMatchStatus.MATCH:
            score += 15.0
        elif legal_name_status == IdentityMatchStatus.MISMATCH:
            score -= 25.0

        if udyam_status in (IdentityMatchStatus.MATCH, IdentityMatchStatus.PARTIAL_MATCH):
            score += 10.0

        if cin_status in (IdentityMatchStatus.MATCH, IdentityMatchStatus.PARTIAL_MATCH):
            score += 10.0

        if address_status == IdentityMatchStatus.MATCH:
            score += 10.0
        elif address_status == IdentityMatchStatus.PARTIAL_MATCH:
            score += 5.0

        # Clamp score in range [0, 100]
        final_score = max(0.0, min(100.0, round(score, 1)))

        # 11. Determine Overall Identity Status
        if pan_gst_status == IdentityMatchStatus.MISMATCH:
            identity_status = OrganizationIdentityStatus.MISMATCH
        elif has_name_mismatch:
            identity_status = OrganizationIdentityStatus.REVIEW_REQUIRED
        elif final_score >= 85.0:
            identity_status = (
                OrganizationIdentityStatus.VERIFIED
                if (verified_pan or verified_gstin)
                else OrganizationIdentityStatus.CONSISTENT
            )
        elif final_score >= 60.0:
            identity_status = OrganizationIdentityStatus.PARTIAL_MATCH
        elif not effective_pan and not effective_gstin:
            identity_status = OrganizationIdentityStatus.UNKNOWN
        else:
            identity_status = OrganizationIdentityStatus.REVIEW_REQUIRED

        # 12. Deactivate previous active assessments
        db.query(OrganizationIdentityAssessment).filter(
            OrganizationIdentityAssessment.organization_id == organization_id,
            OrganizationIdentityAssessment.is_current == True,
        ).update({"is_current": False})

        # 13. Create and persist new Assessment
        assessment = OrganizationIdentityAssessment(
            organization_id=organization_id,
            bid_id=bid_id,
            legal_name_status=legal_name_status,
            pan_status=pan_status,
            gst_status=gst_status,
            cin_status=cin_status,
            udyam_status=udyam_status,
            address_status=address_status,
            pan_gst_embedded_status=pan_gst_status,
            identity_score=final_score,
            identity_status=identity_status,
            signals_json=signals,
            evidence_json=evidence_dict,
            is_current=True,
            evaluated_at=datetime.now(timezone.utc),
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        # 14. Audit Log Event
        try:
            audit_event = AuditEvent(
                organization_id=organization_id,
                event_type=AuditEventType.ORGANIZATION_IDENTITY_CHECKED,
                entity_type=AuditEntityType.ORGANIZATION_IDENTITY_ASSESSMENT,
                entity_id=assessment.id,
                action="EVALUATE_IDENTITY",
                summary=f"Organization identity evaluated: Status={identity_status}, Confidence={final_score}%",
                actor_user_id=actor_id if actor_id else None,
                actor_name=actor_name,
                actor_source=AuditActorSource.SYSTEM if not actor_id else AuditActorSource.HUMAN,
                metadata_json={
                    "identity_status": identity_status,
                    "identity_score": final_score,
                    "pan_gst_status": pan_gst_status,
                    "legal_name_status": legal_name_status,
                },
            )
            db.add(audit_event)
            db.commit()
        except Exception as audit_err:
            logger.warning("Failed to emit audit event for identity check: %s", audit_err)

        return assessment

    def detect_organization_duplicates(
        self,
        db: Session,
        organization_id: uuid.UUID,
        tender_id: Optional[uuid.UUID] = None,
    ) -> List[OrganizationDuplicateMatch]:
        """
        Cross-checks an organization against all other active organizations in the database.
        Disambiguates:
        - SAME LEGAL ENTITY / SHARED IDENTIFIERS (matching PAN, GSTIN, CIN, Udyam)
        - SAME OR SIMILAR NAME BUT DIFFERENT LEGAL IDENTITY (different PAN/GSTIN)
        """
        org_a = db.query(Organization).filter(Organization.id == organization_id).first()
        if not org_a:
            return []

        pan_a = normalize_identifier(org_a.pan_number) if org_a.pan_number else ""
        gstin_a = normalize_identifier(org_a.gstin) if org_a.gstin else ""
        cin_a = normalize_cin(org_a.cin_llpin) if org_a.cin_llpin else ""
        udyam_a = normalize_udyam_number(org_a.udyam_number) if org_a.udyam_number else ""
        name_a = normalize_org_name(org_a.name) if org_a.name else ""

        # Query all other active organizations
        other_orgs = (
            db.query(Organization)
            .filter(Organization.id != organization_id, Organization.is_active == True)
            .all()
        )

        detected_matches: List[OrganizationDuplicateMatch] = []

        for org_b in other_orgs:
            pan_b = normalize_identifier(org_b.pan_number) if org_b.pan_number else ""
            gstin_b = normalize_identifier(org_b.gstin) if org_b.gstin else ""
            cin_b = normalize_cin(org_b.cin_llpin) if org_b.cin_llpin else ""
            udyam_b = normalize_udyam_number(org_b.udyam_number) if org_b.udyam_number else ""
            name_b = normalize_org_name(org_b.name) if org_b.name else ""

            matched_ids: Dict[str, Any] = {}
            match_type: Optional[str] = None
            sim_score = 0.0
            notes = ""

            # Check Strong Identifiers
            same_pan = bool(pan_a and pan_b and pan_a == pan_b)
            same_gstin = bool(gstin_a and gstin_b and gstin_a == gstin_b)
            same_cin = bool(cin_a and cin_b and cin_a == cin_b)
            same_udyam = bool(udyam_a and udyam_b and udyam_a == udyam_b)

            if same_pan:
                matched_ids["pan"] = pan_a
            if same_gstin:
                matched_ids["gstin"] = gstin_a
            if same_cin:
                matched_ids["cin"] = cin_a
            if same_udyam:
                matched_ids["udyam"] = udyam_a

            # Disambiguation Logic
            if same_pan and same_gstin:
                match_type = OrganizationDuplicateMatchType.SAME_LEGAL_ENTITY
                sim_score = 100.0
                notes = "Both organizations share identical primary statutory registrations (PAN and GSTIN)."
            elif same_pan:
                match_type = OrganizationDuplicateMatchType.SAME_PAN
                sim_score = 95.0
                notes = f"Both profiles share the exact same Permanent Account Number ({pan_a})."
            elif same_gstin:
                match_type = OrganizationDuplicateMatchType.SAME_GSTIN
                sim_score = 95.0
                notes = f"Both profiles share the exact same GSTIN ({gstin_a})."
            elif same_cin:
                match_type = OrganizationDuplicateMatchType.SAME_CIN
                sim_score = 90.0
                notes = f"Both profiles share the exact same CIN / LLPIN ({cin_a})."
            elif same_udyam:
                match_type = OrganizationDuplicateMatchType.SAME_UDYAM
                sim_score = 85.0
                notes = f"Both profiles share the exact same Udyam Registration Number ({udyam_a})."
            else:
                # Name-only similarity comparison (Disambiguation Case B)
                if name_a and name_b:
                    m_stat, m_conf = compare_names(org_a.name, org_b.name)
                    if m_stat == VerificationMatchStatus.MATCH or name_a == name_b:
                        match_type = OrganizationDuplicateMatchType.SAME_NAME_DIFFERENT_IDENTITY
                        sim_score = 65.0
                        notes = "Organizations share similar trade/legal names but hold distinct, non-conflicting legal identifiers (PAN/GSTIN)."
                    elif m_stat == VerificationMatchStatus.PARTIAL_MATCH:
                        match_type = OrganizationDuplicateMatchType.HIGH_NAME_SIMILARITY
                        sim_score = 50.0
                        notes = "High textual overlap in business name; distinct statutory credentials registered."

            if match_type:
                # Deterministic ordering for pair uniqueness
                sorted_ids = sorted([organization_id, org_b.id])
                id_a, id_b = sorted_ids[0], sorted_ids[1]

                existing = (
                    db.query(OrganizationDuplicateMatch)
                    .filter(
                        OrganizationDuplicateMatch.organization_a_id == id_a,
                        OrganizationDuplicateMatch.organization_b_id == id_b,
                    )
                    .first()
                )

                if existing:
                    existing.match_type = match_type
                    existing.matched_identifiers = matched_ids
                    existing.similarity_score = sim_score
                    existing.notes = notes
                    if tender_id:
                        existing.tender_id = tender_id
                    db.commit()
                    db.refresh(existing)
                    detected_matches.append(existing)
                else:
                    new_match = OrganizationDuplicateMatch(
                        organization_a_id=id_a,
                        organization_b_id=id_b,
                        tender_id=tender_id,
                        match_type=match_type,
                        matched_identifiers=matched_ids,
                        similarity_score=sim_score,
                        status=OrganizationDuplicateMatchStatus.DETECTED,
                        notes=notes,
                    )
                    db.add(new_match)
                    db.commit()
                    db.refresh(new_match)
                    detected_matches.append(new_match)

                    # Update identity assessment status if duplicate strong identifier found
                    if match_type in (
                        OrganizationDuplicateMatchType.SAME_LEGAL_ENTITY,
                        OrganizationDuplicateMatchType.SAME_PAN,
                        OrganizationDuplicateMatchType.SAME_GSTIN,
                    ):
                        db.query(OrganizationIdentityAssessment).filter(
                            OrganizationIdentityAssessment.organization_id == organization_id,
                            OrganizationIdentityAssessment.is_current == True,
                        ).update({"identity_status": OrganizationIdentityStatus.POTENTIAL_DUPLICATE})
                        db.commit()

        return detected_matches

    def resolve_duplicate_match(
        self,
        db: Session,
        match_id: uuid.UUID,
        user_id: uuid.UUID,
        new_status: str,
        notes: Optional[str] = None,
    ) -> OrganizationDuplicateMatch:
        """
        Records human determination on a duplicate entity match.
        """
        match = db.query(OrganizationDuplicateMatch).filter(OrganizationDuplicateMatch.id == match_id).first()
        if not match:
            raise ValueError(f"Duplicate match {match_id} not found.")

        if new_status not in OrganizationDuplicateMatchStatus.ALL:
            raise ValueError(f"Invalid status {new_status}. Must be one of {OrganizationDuplicateMatchStatus.ALL}")

        match.status = new_status
        match.reviewed_by = user_id
        match.reviewed_at = datetime.now(timezone.utc)
        if notes:
            match.notes = f"{match.notes or ''}\n[Resolution]: {notes}".strip()

        db.commit()
        db.refresh(match)
        return match


organization_identity_service = OrganizationIdentityService()
