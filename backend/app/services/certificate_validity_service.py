"""
Certificate Validity Monitoring Service
Part 14 — Certificate Validity Monitoring for BidVerify AI

Responsibilities:
- Extracts issue and expiry/validity dates from BidDocuments and OCR/Structured extraction results.
- Normalizes diverse date formats and flags ambiguous or low-confidence dates.
- Calculates deterministic validity statuses (VALID, EXPIRING_SOON, EXPIRED, NO_EXPIRY, UNKNOWN, REVIEW_REQUIRED).
- Computes countdown timers across configurable warning thresholds (30d, 7d, 1d).
- Integrates with Document Quality Checks (Part 11) and Verification Adapters (Part 5).
- Integrates with Notification Center (Part 12) with deduplication keys.
- Integrates with Audit Trail (Part 8E).
- Manages document replacement lifecycle (marks old records is_current = False).
- Separates factual validity from compliance decision policies.
"""

from datetime import date, datetime, timezone, timedelta
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select, update, or_, and_
from sqlalchemy.orm import Session, joinedload

from app.db.models.audit_event import (
    AuditEventType,
    AuditEntityType,
    AuditActorSource,
)
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.document_processing import DocumentProcessing, DocumentClass
from app.db.models.document_quality import DocumentQualityResult, QualityLevel
from app.db.models.document_validity import (
    DocumentValidityRecord,
    ValidityStatus,
    ValidityDateSource,
)
from app.db.models.human_review import (
    HumanReviewItem,
    ReviewType,
    ReviewSeverity,
    ReviewStatus,
)
from app.db.models.notification import NotificationSeverity, NotificationType
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.role import Role
from app.db.models.tender import Tender
from app.db.models.user import User
from app.db.models.verification_record import VerificationRecord
from app.schemas.audit import RecordAuditEventDTO
from app.services.audit.audit_service import AuditService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

# Configurable Warning Thresholds (in days)
DEFAULT_THRESHOLD_WARN_DAYS = 30
DEFAULT_THRESHOLD_URGENT_DAYS = 7
DEFAULT_THRESHOLD_CRITICAL_DAYS = 1

# Document classes that are inherently permanent (no expiry)
PERMANENT_DOCUMENT_TYPES = {
    "PAN",
    "PAN_CARD",
    "FINANCIAL_STATEMENT",
    "TURNOVER_CERTIFICATE",
    "EXPERIENCE_CERTIFICATE",
    "BLACKLIST_DECLARATION",
}

# Date parsing month map
MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12
}


class CertificateValidityService:
    """
    Centralized service for evaluating, updating, and monitoring certificate validity.
    """

    # ---------------------------------------------------------------------------
    # 1. Date Extraction & Normalization
    # ---------------------------------------------------------------------------

    @classmethod
    def normalize_date(cls, date_str: str) -> Tuple[Optional[date], float, bool]:
        """
        Parses a date string into a python date object.
        Returns: (parsed_date, confidence_multiplier, is_ambiguous)
        """
        if not date_str:
            return None, 0.0, False

        clean_str = date_str.strip().strip(",.;:")
        clean_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', clean_str, flags=re.IGNORECASE)

        # 1. YYYY-MM-DD or YYYY/MM/DD
        match_ymd = re.search(r'\b(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})\b', clean_str)
        if match_ymd:
            y, m, d = int(match_ymd.group(1)), int(match_ymd.group(2)), int(match_ymd.group(3))
            try:
                return date(y, m, d), 1.0, False
            except ValueError:
                pass

        # 2. Textual month: DD Month YYYY (e.g., 31 March 2027) or Month DD, YYYY (e.g., March 31, 2027)
        match_d_month_y = re.search(r'\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b', clean_str)
        if match_d_month_y:
            d = int(match_d_month_y.group(1))
            m_name = match_d_month_y.group(2).lower()
            y = int(match_d_month_y.group(3))
            m = MONTH_MAP.get(m_name)
            if m:
                try:
                    return date(y, m, d), 1.0, False
                except ValueError:
                    pass

        match_month_d_y = re.search(r'\b([A-Za-z]+)\s+(\d{1,2})(?:,\s*|\s+)(\d{4})\b', clean_str)
        if match_month_d_y:
            m_name = match_month_d_y.group(1).lower()
            d = int(match_month_d_y.group(2))
            y = int(match_month_d_y.group(3))
            m = MONTH_MAP.get(m_name)
            if m:
                try:
                    return date(y, m, d), 1.0, False
                except ValueError:
                    pass

        # 3. Numeric DD/MM/YYYY or DD-MM-YYYY
        match_dmy = re.search(r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b', clean_str)
        if match_dmy:
            v1, v2, y = int(match_dmy.group(1)), int(match_dmy.group(2)), int(match_dmy.group(3))
            # If v1 > 12 -> v1 must be day, v2 is month (standard DD/MM/YYYY)
            if v1 > 12 and 1 <= v2 <= 12:
                try:
                    return date(y, v2, v1), 0.95, False
                except ValueError:
                    pass
            # If v2 > 12 -> v2 must be day, v1 is month (MM/DD/YYYY)
            elif v2 > 12 and 1 <= v1 <= 12:
                try:
                    return date(y, v1, v2), 0.95, False
                except ValueError:
                    pass
            # Both v1 <= 12 and v2 <= 12: In Indian procurement, DD/MM/YYYY is standard
            elif 1 <= v1 <= 12 and 1 <= v2 <= 12:
                # If ambiguous, prefer DD/MM/YYYY but slightly reduce confidence
                try:
                    return date(y, v2, v1), 0.85, (v1 != v2)
                except ValueError:
                    pass

        return None, 0.0, False

    @classmethod
    def extract_validity_dates_from_text(
        cls,
        text: str,
        document_type: str,
    ) -> Dict[str, Any]:
        """
        Scans document text for issue date, expiry date, validity keywords, and evidence.
        """
        result: Dict[str, Any] = {
            "issue_date": None,
            "expiry_date": None,
            "evidence_snippet": None,
            "confidence": 0.5,
            "is_permanent": False,
            "is_ambiguous": False,
            "page": 1,
        }

        if not text:
            if document_type in PERMANENT_DOCUMENT_TYPES:
                result["is_permanent"] = True
                result["confidence"] = 1.0
                result["evidence_snippet"] = f"Document type '{document_type}' is permanently valid."
            return result

        doc_type_upper = (document_type or "").upper()
        if doc_type_upper in PERMANENT_DOCUMENT_TYPES:
            result["is_permanent"] = True
            result["confidence"] = 1.0
            result["evidence_snippet"] = f"Document type '{document_type}' is permanently valid."
            return result

        # Check for Udyam / GST standard permanent cases without explicit expiry
        is_udyam = "UDYAM" in doc_type_upper or "MSME" in doc_type_upper or "udyam" in text.lower()
        is_gst = "GST" in doc_type_upper or "gstin" in text.lower()

        # Regular expressions for Expiry / Validity
        expiry_patterns = [
            r'(?:valid\s*(?:up\s*to|until|upto|till|through)|expiry\s*(?:date)?|expiration\s*(?:date)?|date\s*of\s*expiry|period\s*of\s*validity|validity\s*(?:up\s*to|until|upto|till|period)?|expires\s*on|renewal\s*date)\s*[:\-\s]*([0-9A-Za-z\s,\-\/\.]{6,25})',
            r'(?:valid\s*upto|valid\s*till)\s*[:\-\s]*([0-9A-Za-z\s,\-\/\.]{6,25})',
            r'certificate\s*validity\s*[:\-\s]*([0-9A-Za-z\s,\-\/\.]{6,25})',
        ]

        # Regular expressions for Issue Date
        issue_patterns = [
            r'(?:date\s*of\s*issue|issue\s*date|issued\s*on|date\s*of\s*registration|registration\s*date|with\s*effect\s*from|wef)\s*[:\-\s]*([0-9A-Za-z\s,\-\/\.]{6,25})',
            r'issued\s*dated?\s*[:\-\s]*([0-9A-Za-z\s,\-\/\.]{6,25})',
        ]

        # 1. Search for explicit expiry date
        found_expiry = None
        evidence_snippet = None
        expiry_conf = 0.85

        for pattern in expiry_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw_match_text = match.group(1).strip()
                parsed_d, conf_mult, is_ambig = cls.normalize_date(raw_match_text)
                if parsed_d:
                    found_expiry = parsed_d
                    expiry_conf = 0.90 * conf_mult
                    result["is_ambiguous"] = is_ambig
                    start = max(0, match.start() - 10)
                    end = min(len(text), match.end() + 20)
                    evidence_snippet = text[start:end].replace('\n', ' ').strip()
                    break

        # 2. Search for explicit issue date
        found_issue = None
        for pattern in issue_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw_match_text = match.group(1).strip()
                parsed_d, _, _ = cls.normalize_date(raw_match_text)
                if parsed_d:
                    found_issue = parsed_d
                    if not evidence_snippet:
                        start = max(0, match.start() - 10)
                        end = min(len(text), match.end() + 20)
                        evidence_snippet = text[start:end].replace('\n', ' ').strip()
                    break

        # 3. Check for "Valid for N years / months from issue date"
        if not found_expiry and found_issue:
            duration_match = re.search(r'valid\s*for\s*(\d+)\s*(years?|yrs?|months?)\s*(?:from\s*(?:date\s*of\s*issue|issuance))?', text, re.IGNORECASE)
            if duration_match:
                qty = int(duration_match.group(1))
                unit = duration_match.group(2).lower()
                if "year" in unit or "yr" in unit:
                    found_expiry = date(found_issue.year + qty, found_issue.month, found_issue.day)
                elif "month" in unit:
                    m = found_issue.month + qty
                    y = found_issue.year + (m - 1) // 12
                    m = ((m - 1) % 12) + 1
                    found_expiry = date(y, m, found_issue.day)
                expiry_conf = 0.85
                evidence_snippet = f"Valid for {qty} {unit} from issue date {found_issue.strftime('%d/%m/%Y')}"

        # 4. Handle default validity heuristics for known standard documents
        if not found_expiry:
            if is_udyam or is_gst:
                result["is_permanent"] = True
                result["confidence"] = 0.95
                result["issue_date"] = found_issue
                result["evidence_snippet"] = evidence_snippet or f"{document_type} registered with permanent validity."
                return result
            elif "NSIC" in doc_type_upper and found_issue:
                # NSIC default validity 2 years
                found_expiry = date(found_issue.year + 2, found_issue.month, found_issue.day)
                expiry_conf = 0.75
                evidence_snippet = f"NSIC Standard 2-year validity from issue date {found_issue.strftime('%d/%m/%Y')}"

        result["issue_date"] = found_issue
        result["expiry_date"] = found_expiry
        result["evidence_snippet"] = evidence_snippet
        result["confidence"] = expiry_conf if found_expiry else 0.5
        return result

    # ---------------------------------------------------------------------------
    # 2. Validity Status Evaluation & Thresholds
    # ---------------------------------------------------------------------------

    @classmethod
    def determine_validity_status(
        cls,
        expiry_date: Optional[date],
        is_permanent: bool,
        confidence: float,
        reference_date: Optional[date] = None,
        threshold_warn_days: int = DEFAULT_THRESHOLD_WARN_DAYS,
    ) -> Tuple[ValidityStatus, Optional[int]]:
        """
        Determines the centralized ValidityStatus and days remaining relative to reference_date.
        """
        ref_date = reference_date or date.today()

        if is_permanent:
            return ValidityStatus.NO_EXPIRY, None

        if confidence < 0.60:
            return ValidityStatus.REVIEW_REQUIRED, None

        if not expiry_date:
            return ValidityStatus.UNKNOWN, None

        days_remaining = (expiry_date - ref_date).days

        if days_remaining < 0:
            return ValidityStatus.EXPIRED, days_remaining
        elif days_remaining <= threshold_warn_days:
            return ValidityStatus.EXPIRING_SOON, days_remaining
        else:
            return ValidityStatus.VALID, days_remaining

    # ---------------------------------------------------------------------------
    # 3. Document Evaluation Lifecycle
    # ---------------------------------------------------------------------------

    @classmethod
    def evaluate_document_validity(
        cls,
        db: Session,
        document_id: uuid.UUID,
        reference_date: Optional[date] = None,
        force_recheck: bool = False,
        current_user: Optional[User] = None,
    ) -> DocumentValidityRecord:
        """
        Evaluates and persists the DocumentValidityRecord for a given BidDocument.
        Integrates with DocumentProcessing text, DocumentQualityResult (Part 11),
        VerificationRecord (Part 5), Notification Center (Part 12), and Audit Trail.
        """
        ref_date = reference_date or date.today()

        # 1. Load document with relations
        doc = db.scalars(
            select(BidDocument).where(BidDocument.id == document_id)
        ).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"BidDocument with ID {document_id} not found.",
            )

        # 2. Check if a current record already exists
        existing_record = db.scalars(
            select(DocumentValidityRecord).where(
                DocumentValidityRecord.document_id == document_id,
                DocumentValidityRecord.is_current == True,
            )
        ).first()

        if existing_record and not force_recheck:
            # Re-calculate days_until_expiry and status for current date
            old_status = existing_record.validity_status
            new_status, days_rem = cls.determine_validity_status(
                existing_record.expiry_date,
                existing_record.validity_status == ValidityStatus.NO_EXPIRY.value,
                existing_record.confidence,
                reference_date=ref_date,
            )
            existing_record.days_until_expiry = days_rem
            existing_record.validity_status = new_status.value
            existing_record.last_checked_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing_record)

            # Trigger notification on transition
            cls._dispatch_validity_notifications(db, existing_record, doc)
            return existing_record

        # 3. Load DocumentProcessing & Quality Results
        doc_proc = db.scalars(
            select(DocumentProcessing).where(DocumentProcessing.bid_document_id == document_id)
        ).first()

        doc_quality = db.scalars(
            select(DocumentQualityResult).where(DocumentQualityResult.document_id == document_id)
        ).first()

        verif_record = db.scalars(
            select(VerificationRecord).where(VerificationRecord.bid_document_id == document_id)
        ).first()

        # 4. Extract validity information
        text_corpus = ""
        if doc_proc:
            text_corpus = (doc_proc.raw_text or "") + " " + (doc_proc.normalized_text or "")
        
        extracted = cls.extract_validity_dates_from_text(
            text=text_corpus,
            document_type=doc.document_type or "OTHER",
        )

        issue_date = extracted["issue_date"]
        expiry_date = extracted["expiry_date"]
        is_permanent = extracted["is_permanent"]
        confidence = extracted["confidence"]
        evidence_snippet = extracted["evidence_snippet"]
        is_ambiguous = extracted.get("is_ambiguous", False)

        metadata_dict: Dict[str, Any] = {
            "is_ambiguous_date": is_ambiguous,
            "threshold_warn_days": DEFAULT_THRESHOLD_WARN_DAYS,
        }

        # 5. Integrate Document Quality (Part 11)
        if doc_quality:
            metadata_dict["quality_level"] = doc_quality.quality_level
            metadata_dict["quality_score"] = doc_quality.quality_score
            if doc_quality.quality_level in [QualityLevel.POOR, QualityLevel.UNUSABLE] or doc_quality.is_blurry:
                confidence = min(confidence, 0.45)
                metadata_dict["quality_review_reason"] = "POOR_SCAN_QUALITY"

        # 6. Integrate Official Verification Adapter (Part 5)
        verif_payload = (verif_record.response_payload or verif_record.evidence) if verif_record else None
        if verif_payload:
            verif_expiry_str = verif_payload.get("expiry_date") or verif_payload.get("valid_until")
            if verif_expiry_str:
                verif_d, _, _ = cls.normalize_date(str(verif_expiry_str))
                if verif_d:
                    if expiry_date and verif_d == expiry_date:
                        metadata_dict["verification_adapter_comparison"] = "MATCH"
                        confidence = min(1.0, confidence + 0.1)
                    elif expiry_date and verif_d != expiry_date:
                        metadata_dict["verification_adapter_comparison"] = "MISMATCH"
                        metadata_dict["adapter_expiry_date"] = verif_d.isoformat()
                        confidence = 0.50
                    else:
                        metadata_dict["verification_adapter_comparison"] = "ADAPTER_ONLY"
                        expiry_date = verif_d
                        confidence = 0.95

        # 7. Determine Status & Countdown
        calc_status, days_rem = cls.determine_validity_status(
            expiry_date=expiry_date,
            is_permanent=is_permanent,
            confidence=confidence,
            reference_date=ref_date,
        )

        # 8. Compute submission-time validity if attached to a bid
        submission_validity = None
        bid = None
        if doc.bid_id:
            bid = db.scalars(select(Bid).where(Bid.id == doc.bid_id)).first()
            if bid and bid.submitted_at:
                sub_date = bid.submitted_at.date()
                sub_status, _ = cls.determine_validity_status(
                    expiry_date=expiry_date,
                    is_permanent=is_permanent,
                    confidence=confidence,
                    reference_date=sub_date,
                )
                submission_validity = sub_status.value

        # 9. Create or Update Record
        if existing_record:
            existing_record.issue_date = issue_date
            existing_record.expiry_date = expiry_date
            existing_record.validity_status = calc_status.value
            existing_record.days_until_expiry = days_rem
            existing_record.confidence = confidence
            existing_record.source_text = evidence_snippet
            existing_record.submission_validity_status = submission_validity
            existing_record.last_checked_at = datetime.now(timezone.utc)
            existing_record.metadata_json = metadata_dict
            record = existing_record
        else:
            org_id = (bid.bidder_organization_id if bid else None)
            if not org_id and current_user and current_user.profile:
                org_id = current_user.profile.organization_id

            record = DocumentValidityRecord(
                id=uuid.uuid4(),
                document_id=doc.id,
                bid_id=doc.bid_id,
                organization_id=org_id,
                document_type=doc.document_type or "OTHER",
                issue_date=issue_date,
                expiry_date=expiry_date,
                validity_status=calc_status.value,
                days_until_expiry=days_rem,
                date_source=ValidityDateSource.STRUCTURED_EXTRACTION.value,
                source_page=1,
                source_text=evidence_snippet,
                confidence=confidence,
                is_current=True,
                submission_validity_status=submission_validity,
                last_checked_at=datetime.now(timezone.utc),
                next_check_at=datetime.now(timezone.utc) + timedelta(days=1),
                metadata_json=metadata_dict,
                is_active=True,
            )
            db.add(record)

        db.commit()
        db.refresh(record)

        # 10. Audit Event & Human Review if necessary
        cls._record_audit_event(db, record, doc, current_user)
        if calc_status == ValidityStatus.REVIEW_REQUIRED and bid:
            cls._ensure_human_review_item(db, record, doc, bid)

        # 11. Notification Center Dispatch (Part 12)
        cls._dispatch_validity_notifications(db, record, doc)

        return record

    # ---------------------------------------------------------------------------
    # 4. Replacement Document Flow
    # ---------------------------------------------------------------------------

    @classmethod
    def handle_replacement_document(
        cls,
        db: Session,
        old_document_id: uuid.UUID,
        new_document_id: uuid.UUID,
        current_user: User,
    ) -> DocumentValidityRecord:
        """
        Marks previous document validity records as is_current = False and
        evaluates validity on the newly uploaded replacement document.
        """
        # Mark old records as non-current
        db.execute(
            update(DocumentValidityRecord)
            .where(DocumentValidityRecord.document_id == old_document_id)
            .values(is_current=False, updated_at=datetime.now(timezone.utc))
        )
        db.commit()

        # Evaluate new document validity
        new_record = cls.evaluate_document_validity(
            db=db,
            document_id=new_document_id,
            force_recheck=True,
            current_user=current_user,
        )

        # Record Replacement Audit Event
        AuditService.record_event(
            db=db,
            event_dto=RecordAuditEventDTO(
                event_type=AuditEventType.CERTIFICATE_REPLACED,
                entity_type=AuditEntityType.DOCUMENT_VALIDITY_RECORD,
                entity_id=new_record.id,
                action="REPLACE_CERTIFICATE",
                summary=f"Certificate {new_record.document_type} replaced with new document",
                actor_user_id=current_user.id,
                actor_role=current_user.profile.role.name if current_user.profile and current_user.profile.role else None,
                actor_source=AuditActorSource.HUMAN,
                organization_id=new_record.organization_id,
                bid_id=new_record.bid_id,
                metadata={
                    "old_document_id": str(old_document_id),
                    "new_document_id": str(new_document_id),
                    "new_validity_status": new_record.validity_status,
                    "new_expiry_date": new_record.expiry_date.isoformat() if new_record.expiry_date else None,
                },
            ),
        )

        return new_record

    # ---------------------------------------------------------------------------
    # 5. Periodic Validity Batch Re-check
    # ---------------------------------------------------------------------------

    @classmethod
    def run_periodic_validity_checks(
        cls,
        db: Session,
        reference_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Periodic scheduled job / CLI runner that re-evaluates all current certificate records.
        """
        ref_date = reference_date or date.today()
        current_records = db.scalars(
            select(DocumentValidityRecord).where(
                DocumentValidityRecord.is_current == True,
                DocumentValidityRecord.is_active == True,
            )
        ).all()

        checked_count = 0
        transitioned_count = 0
        status_counts = {
            ValidityStatus.VALID.value: 0,
            ValidityStatus.EXPIRING_SOON.value: 0,
            ValidityStatus.EXPIRED.value: 0,
            ValidityStatus.NO_EXPIRY.value: 0,
            ValidityStatus.UNKNOWN.value: 0,
            ValidityStatus.REVIEW_REQUIRED.value: 0,
        }

        for record in current_records:
            checked_count += 1
            old_status = record.validity_status

            new_status, days_rem = cls.determine_validity_status(
                expiry_date=record.expiry_date,
                is_permanent=record.validity_status == ValidityStatus.NO_EXPIRY.value,
                confidence=record.confidence,
                reference_date=ref_date,
            )

            record.days_until_expiry = days_rem
            record.validity_status = new_status.value
            record.last_checked_at = datetime.now(timezone.utc)
            status_counts[new_status.value] = status_counts.get(new_status.value, 0) + 1

            if old_status != new_status.value:
                transitioned_count += 1

            # Check and dispatch notifications
            doc = db.scalars(select(BidDocument).where(BidDocument.id == record.document_id)).first()
            if doc:
                cls._dispatch_validity_notifications(db, record, doc)

        db.commit()

        return {
            "total_checked": checked_count,
            "status_transitions": transitioned_count,
            "status_breakdown": status_counts,
            "reference_date": ref_date.isoformat(),
        }

    # ---------------------------------------------------------------------------
    # 6. Notification Dispatch Helper
    # ---------------------------------------------------------------------------

    @classmethod
    def _dispatch_validity_notifications(
        cls,
        db: Session,
        record: DocumentValidityRecord,
        doc: BidDocument,
    ):
        """
        Dispatches deduplicated notifications for certificate validity alerts.
        """
        if not record.organization_id:
            return

        # Find profiles in bidder organization to notify
        bidder_profiles = db.scalars(
            select(Profile).where(Profile.organization_id == record.organization_id)
        ).all()

        doc_name = doc.document_name or doc.document_type or "Certificate"
        days = record.days_until_expiry

        # A. Expired Certificate Alert
        if record.validity_status == ValidityStatus.EXPIRED.value:
            for prof in bidder_profiles:
                NotificationService.create_notification(
                    db=db,
                    recipient_profile_id=prof.id,
                    organization_id=record.organization_id,
                    notification_type=NotificationType.CERTIFICATE_EXPIRED,
                    severity=NotificationSeverity.CRITICAL,
                    title="Certificate Expired",
                    message=f"Your {doc_name} has expired. Please upload an updated certificate.",
                    bid_id=record.bid_id,
                    document_id=record.document_id,
                    action_url=f"/bidder/certificates",
                    dedupe_key=f"cert_expired:{record.document_id}",
                    cooldown_hours=24,
                )

        # B. Expiring Soon Alert
        elif record.validity_status == ValidityStatus.EXPIRING_SOON.value and days is not None:
            # 1-day threshold
            if days <= 1:
                for prof in bidder_profiles:
                    NotificationService.create_notification(
                        db=db,
                        recipient_profile_id=prof.id,
                        organization_id=record.organization_id,
                        notification_type=NotificationType.CERTIFICATE_EXPIRING,
                        severity=NotificationSeverity.CRITICAL,
                        title="Certificate Expiring Imminently",
                        message=f"Your {doc_name} expires in {days} day(s). Immediate renewal required.",
                        bid_id=record.bid_id,
                        document_id=record.document_id,
                        action_url=f"/bidder/certificates",
                        dedupe_key=f"cert_expiry:{record.document_id}:1d",
                        cooldown_hours=24,
                    )
            # 7-day threshold
            elif days <= 7:
                for prof in bidder_profiles:
                    NotificationService.create_notification(
                        db=db,
                        recipient_profile_id=prof.id,
                        organization_id=record.organization_id,
                        notification_type=NotificationType.CERTIFICATE_EXPIRING,
                        severity=NotificationSeverity.WARNING,
                        title="Certificate Expiring Soon (7 Days)",
                        message=f"Your {doc_name} expires in {days} days. Please prepare an updated certificate.",
                        bid_id=record.bid_id,
                        document_id=record.document_id,
                        action_url=f"/bidder/certificates",
                        dedupe_key=f"cert_expiry:{record.document_id}:7d",
                        cooldown_hours=48,
                    )
            # 30-day threshold
            elif days <= 30:
                for prof in bidder_profiles:
                    NotificationService.create_notification(
                        db=db,
                        recipient_profile_id=prof.id,
                        organization_id=record.organization_id,
                        notification_type=NotificationType.CERTIFICATE_EXPIRING,
                        severity=NotificationSeverity.WARNING,
                        title="Certificate Expiry Reminder (30 Days)",
                        message=f"Your {doc_name} will expire in {days} days on {record.expiry_date.strftime('%d/%m/%Y')}.",
                        bid_id=record.bid_id,
                        document_id=record.document_id,
                        action_url=f"/bidder/certificates",
                        dedupe_key=f"cert_expiry:{record.document_id}:30d",
                        cooldown_hours=72,
                    )

        # C. Review Required Alert
        elif record.validity_status == ValidityStatus.REVIEW_REQUIRED.value:
            for prof in bidder_profiles:
                NotificationService.create_notification(
                    db=db,
                    recipient_profile_id=prof.id,
                    organization_id=record.organization_id,
                    notification_type=NotificationType.CERTIFICATE_VALIDITY_REVIEW_REQUIRED,
                    severity=NotificationSeverity.WARNING,
                    title="Certificate Validity Review Required",
                    message=f"Validity date could not be confirmed with high confidence for your {doc_name}. Please review the uploaded document.",
                    bid_id=record.bid_id,
                    document_id=record.document_id,
                    action_url=f"/bidder/certificates",
                    dedupe_key=f"cert_review:{record.document_id}",
                    cooldown_hours=48,
                )

    # ---------------------------------------------------------------------------
    # 7. Audit Logging & Human Review Helpers
    # ---------------------------------------------------------------------------

    @classmethod
    def _record_audit_event(
        cls,
        db: Session,
        record: DocumentValidityRecord,
        doc: BidDocument,
        current_user: Optional[User] = None,
    ):
        event_type = AuditEventType.CERTIFICATE_VALIDITY_CHECKED
        if record.validity_status == ValidityStatus.EXPIRED.value:
            event_type = AuditEventType.CERTIFICATE_EXPIRED
        elif record.validity_status == ValidityStatus.EXPIRING_SOON.value:
            event_type = AuditEventType.CERTIFICATE_EXPIRING
        elif record.validity_status == ValidityStatus.REVIEW_REQUIRED.value:
            event_type = AuditEventType.CERTIFICATE_VALIDITY_REVIEW_REQUIRED

        AuditService.record_event(
            db=db,
            event_dto=RecordAuditEventDTO(
                event_type=event_type,
                entity_type=AuditEntityType.DOCUMENT_VALIDITY_RECORD,
                entity_id=record.id,
                action="EVALUATE_CERTIFICATE_VALIDITY",
                summary=f"Certificate {record.document_type} evaluated as {record.validity_status}",
                actor_user_id=current_user.id if current_user else None,
                actor_role=current_user.profile.role.name if current_user and current_user.profile and current_user.profile.role else "SYSTEM",
                actor_source=AuditActorSource.HUMAN if current_user else AuditActorSource.SYSTEM,
                organization_id=record.organization_id,
                bid_id=record.bid_id,
                metadata={
                    "document_id": str(record.document_id),
                    "document_type": record.document_type,
                    "validity_status": record.validity_status,
                    "expiry_date": record.expiry_date.isoformat() if record.expiry_date else None,
                    "days_until_expiry": record.days_until_expiry,
                    "confidence": record.confidence,
                },
            ),
        )

    @classmethod
    def _ensure_human_review_item(
        cls,
        db: Session,
        record: DocumentValidityRecord,
        doc: BidDocument,
        bid: Bid,
    ):
        """
        Creates a HumanReviewItem queue item if certificate validity is uncertain/conflicted.
        """
        existing = db.scalars(
            select(HumanReviewItem).where(
                HumanReviewItem.bid_id == bid.id,
                HumanReviewItem.bid_document_id == doc.id,
                HumanReviewItem.review_type == ReviewType.COMPLIANCE_REVIEW,
                HumanReviewItem.status.in_([ReviewStatus.OPEN, ReviewStatus.IN_REVIEW]),
            )
        ).first()

        if not existing:
            item = HumanReviewItem(
                id=uuid.uuid4(),
                organization_id=record.organization_id,
                tender_id=bid.tender_id,
                bid_id=bid.id,
                bid_document_id=doc.id,
                review_type=ReviewType.COMPLIANCE_REVIEW,
                severity=ReviewSeverity.MEDIUM,
                status=ReviewStatus.OPEN,
                source_type="DOCUMENT_VALIDITY_RECORD",
                source_id=record.id.hex,
                title=f"Verify Certificate Expiry: {doc.document_name or doc.document_type}",
                reason="Certificate validity date extraction is uncertain or conflicting with scan quality.",
                system_finding={
                    "validity_status": record.validity_status,
                    "confidence": record.confidence,
                    "evidence_snippet": record.source_text,
                    "expiry_date": record.expiry_date.isoformat() if record.expiry_date else None,
                },
            )
            db.add(item)
            db.commit()

    # ---------------------------------------------------------------------------
    # 8. Query & Summary Methods
    # ---------------------------------------------------------------------------

    @classmethod
    def get_bidder_certificates(
        cls,
        db: Session,
        organization_id: uuid.UUID,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        Returns paginated certificate validity records for a bidder organization.
        """
        query = (
            select(DocumentValidityRecord)
            .options(joinedload(DocumentValidityRecord.document))
            .where(
                DocumentValidityRecord.organization_id == organization_id,
                DocumentValidityRecord.is_current == True,
                DocumentValidityRecord.is_active == True,
            )
        )

        if status_filter:
            query = query.where(DocumentValidityRecord.validity_status == status_filter.upper())

        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.join(BidDocument).where(
                or_(
                    BidDocument.document_name.ilike(search_pattern),
                    BidDocument.document_type.ilike(search_pattern),
                    DocumentValidityRecord.source_text.ilike(search_pattern),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = db.scalar(count_stmt) or 0

        # Paginate
        offset = (page - 1) * page_size
        records = db.scalars(
            query.order_by(
                DocumentValidityRecord.expiry_date.asc().nulls_last(),
                DocumentValidityRecord.created_at.desc(),
            )
            .offset(offset)
            .limit(page_size)
        ).all()

        # Aggregate summary stats across all current certificates of organization
        stats_query = (
            select(
                DocumentValidityRecord.validity_status,
                func.count(DocumentValidityRecord.id),
            )
            .where(
                DocumentValidityRecord.organization_id == organization_id,
                DocumentValidityRecord.is_current == True,
                DocumentValidityRecord.is_active == True,
            )
            .group_by(DocumentValidityRecord.validity_status)
        )
        stats_rows = db.execute(stats_query).all()
        status_counts = {row[0]: row[1] for row in stats_rows}

        total_certs = sum(status_counts.values())
        valid_count = status_counts.get(ValidityStatus.VALID.value, 0)
        expiring_soon_count = status_counts.get(ValidityStatus.EXPIRING_SOON.value, 0)
        expired_count = status_counts.get(ValidityStatus.EXPIRED.value, 0)
        no_expiry_count = status_counts.get(ValidityStatus.NO_EXPIRY.value, 0)
        review_required_count = status_counts.get(ValidityStatus.REVIEW_REQUIRED.value, 0)
        unknown_count = status_counts.get(ValidityStatus.UNKNOWN.value, 0)

        total_pages = max(1, (total + page_size - 1) // page_size)

        return {
            "items": records,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "stats": {
                "total_monitored": total_certs,
                "valid_count": valid_count,
                "expiring_soon_count": expiring_soon_count,
                "expired_count": expired_count,
                "no_expiry_count": no_expiry_count,
                "review_required_count": review_required_count,
                "unknown_count": unknown_count,
            },
        }

    @classmethod
    def get_procurement_certificates(
        cls,
        db: Session,
        tender_id: Optional[uuid.UUID] = None,
        bid_id: Optional[uuid.UUID] = None,
        organization_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        Returns paginated certificate validity records for Procurement Officers and Admins.
        """
        query = (
            select(DocumentValidityRecord)
            .options(
                joinedload(DocumentValidityRecord.document),
                joinedload(DocumentValidityRecord.organization),
            )
            .where(
                DocumentValidityRecord.is_current == True,
                DocumentValidityRecord.is_active == True,
            )
        )

        if bid_id:
            query = query.where(DocumentValidityRecord.bid_id == bid_id)
        elif tender_id:
            query = query.join(Bid, DocumentValidityRecord.bid_id == Bid.id).where(Bid.tender_id == tender_id)
        elif organization_id:
            query = query.where(DocumentValidityRecord.organization_id == organization_id)

        if status_filter:
            query = query.where(DocumentValidityRecord.validity_status == status_filter.upper())

        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.join(BidDocument).where(
                or_(
                    BidDocument.document_name.ilike(search_pattern),
                    BidDocument.document_type.ilike(search_pattern),
                    DocumentValidityRecord.source_text.ilike(search_pattern),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = db.scalar(count_stmt) or 0

        # Paginate
        offset = (page - 1) * page_size
        records = db.scalars(
            query.order_by(
                DocumentValidityRecord.expiry_date.asc().nulls_last(),
                DocumentValidityRecord.created_at.desc(),
            )
            .offset(offset)
            .limit(page_size)
        ).all()

        total_pages = max(1, (total + page_size - 1) // page_size)

        return {
            "items": records,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
