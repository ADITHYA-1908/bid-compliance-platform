"""
Document Quality Service for Part 11: Advanced Document Quality Check
Provides deterministic computer vision diagnostics before and during Document AI processing:
- OpenCV Laplacian variance blur / sharpness detection
- Blank page identification (pixel variance & white-ratio thresholding)
- Low resolution & DPI boundary validation
- Skew / rotation angle detection & safe OpenCV preprocessing
- Malformed, corrupted, and password-protected PDF handling
- Deterministic 0-100 quality scoring and level classification (GOOD, ACCEPTABLE, POOR, UNUSABLE)
- Plain-English bidder feedback generation and auditable procurement telemetry
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import cv2
import fitz  # PyMuPDF
import numpy as np
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.db.models.audit_event import AuditActorSource, AuditEntityType, AuditEventType
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.document_processing import DocumentProcessing
from app.db.models.document_quality import (
    DocumentPageQuality,
    DocumentQualityResult,
    QualityLevel,
)
from app.db.models.profile import Profile
from app.db.models.tender import Tender
from app.db.models.user import User
from app.schemas.audit import RecordAuditEventDTO
from app.services.audit.audit_service import AuditService
from app.services.bid_document_service import _get_bid_for_bidder
from app.services.image_preprocessing_service import (
    calculate_image_sharpness,
    load_image_bytes_to_cv2,
)
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


class DocumentQualityService:
    """
    Orchestrates deterministic document quality evaluation, page diagnostics,
    scoring, bidder feedback, and integration with Document AI.
    """

    @classmethod
    def evaluate_document_quality(
        cls,
        db: Session,
        doc: BidDocument,
        file_bytes: bytes,
        proc: Optional[DocumentProcessing] = None,
        user: Optional[User] = None,
    ) -> DocumentQualityResult:
        """
        Executes comprehensive multi-signal quality check across all document pages.
        Persists DocumentQualityResult and DocumentPageQuality records in DB.
        """
        now = datetime.now(timezone.utc)
        doc_id = doc.id
        processing_id = proc.id if proc else None

        # Check existing record to update or create new
        quality_result = db.scalars(
            select(DocumentQualityResult)
            .options(joinedload(DocumentQualityResult.page_qualities))
            .where(DocumentQualityResult.document_id == doc_id)
        ).first()

        if not quality_result:
            quality_result = DocumentQualityResult(
                id=uuid.uuid4(),
                document_id=doc_id,
                processing_id=processing_id,
                created_at=now,
                updated_at=now,
            )
            db.add(quality_result)
            db.flush()
        else:
            quality_result.processing_id = processing_id
            quality_result.updated_at = now
            # Clear old page qualities to refresh
            for pq in list(quality_result.page_qualities):
                db.delete(pq)
            db.flush()

        # ---------------------------------------------------------------------
        # Case 1: Empty or missing binary bytes
        # ---------------------------------------------------------------------
        if not file_bytes or len(file_bytes) == 0:
            quality_result.quality_score = 0.0
            quality_result.quality_level = QualityLevel.UNUSABLE
            quality_result.is_corrupted = True
            quality_result.review_required = True
            quality_result.page_count = 0
            quality_result.review_reasons = ["Document file contains 0 bytes (empty file)."]
            quality_result.bidder_feedback = ["Uploaded document is empty (0 bytes). Please upload a valid copy."]
            quality_result.metrics_summary = {"error": "EMPTY_BINARY"}
            db.commit()
            db.refresh(quality_result)
            cls._record_quality_audit(db, doc, quality_result, user)
            return quality_result

        mime_type = (doc.mime_type or "").lower()
        filename = (doc.original_filename or "").lower()
        is_pdf = mime_type == "application/pdf" or filename.endswith(".pdf")

        # ---------------------------------------------------------------------
        # Case 2: Process PDF Document
        # ---------------------------------------------------------------------
        if is_pdf:
            return cls._evaluate_pdf_document(db, doc, file_bytes, quality_result, user)

        # ---------------------------------------------------------------------
        # Case 3: Process Standalone Image Document (PNG, JPG, JPEG)
        # ---------------------------------------------------------------------
        return cls._evaluate_image_document(db, doc, file_bytes, quality_result, user)

    @classmethod
    def _evaluate_pdf_document(
        cls,
        db: Session,
        doc: BidDocument,
        pdf_bytes: bytes,
        quality_result: DocumentQualityResult,
        user: Optional[User] = None,
    ) -> DocumentQualityResult:
        """Evaluates multi-page PDF document structure, rendering, blur, blank, and skew."""
        try:
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as open_err:
            err_str = str(open_err).lower()
            is_encrypted = "password" in err_str or "encrypted" in err_str or "authenticate" in err_str
            logger.warning("PDF open failed for document %s: %s (encrypted=%s)", doc.id, open_err, is_encrypted)

            quality_result.quality_score = 0.0
            quality_result.quality_level = QualityLevel.UNUSABLE
            quality_result.is_password_protected = is_encrypted
            quality_result.is_corrupted = not is_encrypted
            quality_result.review_required = True
            quality_result.page_count = 0

            if is_encrypted:
                quality_result.review_reasons = ["PDF is password-protected / encrypted."]
                quality_result.bidder_feedback = ["Uploaded PDF is password-protected. Please upload an unlocked PDF."]
            else:
                quality_result.review_reasons = [f"PDF binary stream corrupted: {open_err}"]
                quality_result.bidder_feedback = ["Uploaded PDF appears corrupted or unreadable. Please upload a valid document."]

            quality_result.metrics_summary = {"error": "ENCRYPTED_OR_CORRUPT", "details": str(open_err)}
            db.commit()
            db.refresh(quality_result)
            cls._record_quality_audit(db, doc, quality_result, user)
            return quality_result

        try:
            # Check if PDF requires password
            if pdf_doc.needs_pass or pdf_doc.is_encrypted:
                quality_result.quality_score = 0.0
                quality_result.quality_level = QualityLevel.UNUSABLE
                quality_result.is_password_protected = True
                quality_result.review_required = True
                quality_result.page_count = pdf_doc.page_count or 0
                quality_result.review_reasons = ["PDF requires password authentication to view."]
                quality_result.bidder_feedback = ["Uploaded PDF is password-protected. Please upload an unlocked PDF."]
                quality_result.metrics_summary = {"error": "PASSWORD_PROTECTED"}
                db.commit()
                db.refresh(quality_result)
                cls._record_quality_audit(db, doc, quality_result, user)
                return quality_result

            page_count = pdf_doc.page_count
            quality_result.page_count = page_count

            if page_count == 0:
                quality_result.quality_score = 0.0
                quality_result.quality_level = QualityLevel.UNUSABLE
                quality_result.is_corrupted = True
                quality_result.review_required = True
                quality_result.review_reasons = ["PDF contains 0 pages."]
                quality_result.bidder_feedback = ["Uploaded document contains no readable pages. Please upload a complete copy."]
                quality_result.metrics_summary = {"error": "ZERO_PAGES"}
                db.commit()
                db.refresh(quality_result)
                cls._record_quality_audit(db, doc, quality_result, user)
                return quality_result

            # Evaluate each page
            page_diagnostics: List[Dict[str, Any]] = []
            has_blurry = False
            has_blank = False
            has_unreadable = False
            has_low_res = False
            has_skewed = False

            for page_idx in range(page_count):
                page_num = page_idx + 1
                page = pdf_doc.load_page(page_idx)
                diag = cls._diagnose_single_page(page, page_num)
                page_diagnostics.append(diag)

                if diag["is_blurry"]:
                    has_blurry = True
                if diag["is_blank"]:
                    has_blank = True
                if diag["is_unreadable"]:
                    has_unreadable = True
                if diag["is_low_res"]:
                    has_low_res = True
                if diag["is_skewed"]:
                    has_skewed = True

                # Persist DocumentPageQuality entity
                page_quality = DocumentPageQuality(
                    id=uuid.uuid4(),
                    quality_result_id=quality_result.id,
                    document_id=doc.id,
                    page_number=page_num,
                    blur_score=diag["blur_score"],
                    width=diag["width"],
                    height=diag["height"],
                    dpi=diag["dpi"],
                    resolution=f"{diag['width']}x{diag['height']}",
                    ocr_confidence=None,
                    is_blank=diag["is_blank"],
                    is_unreadable=diag["is_unreadable"],
                    is_skewed=diag["is_skewed"],
                    skew_angle=diag["skew_angle"],
                    quality_level=diag["quality_level"],
                    review_reason=diag["review_reason"],
                    issues=diag["issues"],
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(page_quality)

            quality_result.is_blurry = has_blurry
            quality_result.has_blank_pages = has_blank
            quality_result.has_unreadable_pages = has_unreadable
            quality_result.has_low_resolution_pages = has_low_res
            quality_result.has_skewed_pages = has_skewed
            quality_result.is_corrupted = False
            quality_result.is_password_protected = False

            # Compute overall score and level
            score, level, review_req, reasons, feedback = cls._compute_overall_quality(
                page_diagnostics=page_diagnostics,
                is_corrupted=False,
                is_password_protected=False,
            )

            quality_result.quality_score = score
            quality_result.quality_level = level
            quality_result.review_required = review_req
            quality_result.review_reasons = reasons
            quality_result.bidder_feedback = feedback
            quality_result.metrics_summary = {
                "total_pages": page_count,
                "blurry_pages_count": sum(1 for p in page_diagnostics if p["is_blurry"]),
                "blank_pages_count": sum(1 for p in page_diagnostics if p["is_blank"]),
                "unreadable_pages_count": sum(1 for p in page_diagnostics if p["is_unreadable"]),
                "low_res_pages_count": sum(1 for p in page_diagnostics if p["is_low_res"]),
                "skewed_pages_count": sum(1 for p in page_diagnostics if p["is_skewed"]),
                "avg_sharpness": float(np.mean([p["blur_score"] for p in page_diagnostics])) if page_diagnostics else 0.0,
            }

            db.commit()
            db.refresh(quality_result)
            cls._record_quality_audit(db, doc, quality_result, user)
            return quality_result

        finally:
            pdf_doc.close()

    @classmethod
    def _evaluate_image_document(
        cls,
        db: Session,
        doc: BidDocument,
        image_bytes: bytes,
        quality_result: DocumentQualityResult,
        user: Optional[User] = None,
    ) -> DocumentQualityResult:
        """Evaluates single-page standalone image document (PNG/JPG/JPEG)."""
        try:
            img = load_image_bytes_to_cv2(image_bytes)
        except Exception as decode_err:
            logger.warning("Image decode failed for document %s: %s", doc.id, decode_err)
            quality_result.quality_score = 0.0
            quality_result.quality_level = QualityLevel.UNUSABLE
            quality_result.is_corrupted = True
            quality_result.review_required = True
            quality_result.page_count = 1
            quality_result.review_reasons = [f"Image decode failed: {decode_err}"]
            quality_result.bidder_feedback = ["Uploaded image file is corrupted. Please upload a clear image (PNG or JPEG)."]
            quality_result.metrics_summary = {"error": "IMAGE_DECODE_FAILED"}
            db.commit()
            db.refresh(quality_result)
            cls._record_quality_audit(db, doc, quality_result, user)
            return quality_result

        diag = cls._diagnose_image_matrix(img, page_num=1, digital_text_chars=0)
        page_diagnostics = [diag]

        # Persist DocumentPageQuality entity
        page_quality = DocumentPageQuality(
            id=uuid.uuid4(),
            quality_result_id=quality_result.id,
            document_id=doc.id,
            page_number=1,
            blur_score=diag["blur_score"],
            width=diag["width"],
            height=diag["height"],
            dpi=diag["dpi"],
            resolution=f"{diag['width']}x{diag['height']}",
            ocr_confidence=None,
            is_blank=diag["is_blank"],
            is_unreadable=diag["is_unreadable"],
            is_skewed=diag["is_skewed"],
            skew_angle=diag["skew_angle"],
            quality_level=diag["quality_level"],
            review_reason=diag["review_reason"],
            issues=diag["issues"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(page_quality)

        quality_result.page_count = 1
        quality_result.is_blurry = diag["is_blurry"]
        quality_result.has_blank_pages = diag["is_blank"]
        quality_result.has_unreadable_pages = diag["is_unreadable"]
        quality_result.has_low_resolution_pages = diag["is_low_res"]
        quality_result.has_skewed_pages = diag["is_skewed"]
        quality_result.is_corrupted = False
        quality_result.is_password_protected = False

        score, level, review_req, reasons, feedback = cls._compute_overall_quality(
            page_diagnostics=page_diagnostics,
            is_corrupted=False,
            is_password_protected=False,
        )

        quality_result.quality_score = score
        quality_result.quality_level = level
        quality_result.review_required = review_req
        quality_result.review_reasons = reasons
        quality_result.bidder_feedback = feedback
        quality_result.metrics_summary = {
            "total_pages": 1,
            "sharpness": diag["blur_score"],
            "resolution": f"{diag['width']}x{diag['height']}",
            "skew_angle": diag["skew_angle"],
        }

        db.commit()
        db.refresh(quality_result)
        cls._record_quality_audit(db, doc, quality_result, user)
        return quality_result

    @classmethod
    def _diagnose_single_page(cls, page: fitz.Page, page_num: int) -> Dict[str, Any]:
        """Renders and diagnoses a single PyMuPDF PDF page."""
        raw_text = page.get_text() or ""
        digital_text_chars = len(raw_text.strip())

        # Render page at 150 DPI for deterministic CV analysis
        dpi = int(settings.MIN_IMAGE_DPI) if settings.MIN_IMAGE_DPI >= 150 else 150
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, 3))
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        return cls._diagnose_image_matrix(img_bgr, page_num=page_num, digital_text_chars=digital_text_chars)

    @classmethod
    def _diagnose_image_matrix(
        cls,
        img_bgr: np.ndarray,
        page_num: int,
        digital_text_chars: int = 0,
    ) -> Dict[str, Any]:
        """Calculates blur, resolution, blank page, and skew diagnostics on an OpenCV image matrix."""
        height, width = img_bgr.shape[:2]
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # 1. Blur Detection using Laplacian Variance
        sharpness = calculate_image_sharpness(gray)
        # If the page already has abundant native digital text, sharpness is naturally acceptable
        has_native_digital_text = digital_text_chars >= 50
        is_blurry = (sharpness < settings.BLUR_THRESHOLD) and (not has_native_digital_text)

        # 2. Blank Page Detection
        # Check pixel variance and pure-white pixel proportion
        pixel_variance = float(np.var(gray))
        white_pixels_ratio = float(np.sum(gray >= 250)) / float(gray.size)
        is_blank = (
            digital_text_chars < 15
            and (
                pixel_variance < settings.BLANK_PAGE_PIXEL_VAR_THRESHOLD
                or white_pixels_ratio >= settings.BLANK_PAGE_WHITE_RATIO_THRESHOLD
            )
        )

        # 3. Resolution & Dimension Check
        is_low_res = (width < settings.MIN_IMAGE_WIDTH) or (height < settings.MIN_IMAGE_HEIGHT)

        # 4. Skew / Rotation Angle Detection
        skew_angle = 0.0
        is_skewed = False
        try:
            pts = cv2.findNonZero((gray < 235).astype(np.uint8))
            if pts is not None and len(pts) >= 100:
                rect = cv2.minAreaRect(pts)
                angle = rect[-1]
                if angle < -45:
                    angle = -(90 + angle)
                else:
                    angle = -angle

                if abs(angle) >= 0.5 and abs(angle) <= 45.0:
                    skew_angle = round(float(angle), 2)
                    if abs(skew_angle) >= settings.SKEW_ANGLE_THRESHOLD:
                        is_skewed = True
        except Exception:
            skew_angle = 0.0
            is_skewed = False

        # 5. Unreadable Check
        is_unreadable = False
        if not is_blank:
            if (is_blurry and is_low_res) or (not has_native_digital_text and sharpness < 15.0):
                is_unreadable = True

        # 6. Page Issues and Reasons
        issues: List[str] = []
        if is_blank:
            issues.append(f"Page {page_num} detected as blank (white ratio {white_pixels_ratio:.1%}).")
        if is_unreadable:
            issues.append(f"Page {page_num} is unreadable (extremely low sharpness: {sharpness:.1f}).")
        elif is_blurry:
            issues.append(f"Page {page_num} has blur (sharpness {sharpness:.1f} < {settings.BLUR_THRESHOLD}).")
        if is_low_res:
            issues.append(f"Page {page_num} is low resolution ({width}x{height} < {settings.MIN_IMAGE_WIDTH}x{settings.MIN_IMAGE_HEIGHT}).")
        if is_skewed:
            issues.append(f"Page {page_num} has significant skew angle ({skew_angle}°).")

        # 7. Page Quality Level
        if is_unreadable:
            quality_level = QualityLevel.UNUSABLE
            review_reason = f"Page {page_num} is unreadable due to severe blur/degradation."
        elif is_blank:
            quality_level = QualityLevel.POOR
            review_reason = f"Page {page_num} appears to be completely blank."
        elif is_blurry or is_low_res or is_skewed:
            quality_level = QualityLevel.POOR if (is_blurry and is_skewed) else QualityLevel.ACCEPTABLE
            review_reason = "; ".join(issues)
        else:
            quality_level = QualityLevel.GOOD
            review_reason = None

        return {
            "page_number": page_num,
            "width": width,
            "height": height,
            "dpi": int(settings.MIN_IMAGE_DPI),
            "blur_score": round(sharpness, 2),
            "skew_angle": skew_angle,
            "is_blurry": is_blurry,
            "is_blank": is_blank,
            "is_low_res": is_low_res,
            "is_skewed": is_skewed,
            "is_unreadable": is_unreadable,
            "has_native_digital_text": has_native_digital_text,
            "issues": issues,
            "quality_level": quality_level,
            "review_reason": review_reason,
        }

    @classmethod
    def _compute_overall_quality(
        cls,
        page_diagnostics: List[Dict[str, Any]],
        is_corrupted: bool = False,
        is_password_protected: bool = False,
    ) -> Tuple[float, str, bool, List[str], List[str]]:
        """
        Deterministic scoring algorithm (0-100) mapping diagnostics to QualityLevel,
        review_required flag, technical reasons, and bidder feedback.
        """
        if is_corrupted or is_password_protected:
            return 0.0, QualityLevel.UNUSABLE, True, ["Document corrupted or encrypted."], ["Please upload a valid, unlocked PDF copy."]

        total_pages = len(page_diagnostics)
        if total_pages == 0:
            return 0.0, QualityLevel.UNUSABLE, True, ["Zero readable pages found."], ["Document contains no readable pages."]

        # Check if 100% of pages are blank
        all_blank = all(p["is_blank"] for p in page_diagnostics)
        if all_blank:
            return (
                0.0,
                QualityLevel.UNUSABLE,
                True,
                ["All pages in the document are blank."],
                ["All pages in the uploaded document are blank. Please upload the complete document."],
            )

        # Base score 100
        score = 100.0
        reasons: List[str] = []
        feedback_set: List[str] = []

        # Deduct for unreadable pages
        unreadable_count = sum(1 for p in page_diagnostics if p["is_unreadable"])
        if unreadable_count > 0:
            penalty = min(60.0, unreadable_count * 30.0)
            score -= penalty
            reasons.append(f"{unreadable_count} page(s) are severely unreadable.")
            feedback_set.append(f"{unreadable_count} page(s) appear unreadable. Please ensure all pages are legible.")

        # Deduct for blurry pages
        blurry_count = sum(1 for p in page_diagnostics if p["is_blurry"])
        if blurry_count > 0:
            penalty = min(30.0, blurry_count * 15.0)
            score -= penalty
            reasons.append(f"{blurry_count} page(s) have blur below threshold ({settings.BLUR_THRESHOLD}).")
            feedback_set.append("Document scan contains blurry pages. Please upload a sharper copy.")

        # Deduct for mixed blank pages
        blank_count = sum(1 for p in page_diagnostics if p["is_blank"])
        if blank_count > 0 and not all_blank:
            penalty = min(30.0, blank_count * 15.0)
            score -= penalty
            reasons.append(f"{blank_count} blank page(s) detected in document.")
            feedback_set.append("Some pages appear blank. Please verify all document pages are included.")

        # Deduct for low resolution
        low_res_count = sum(1 for p in page_diagnostics if p["is_low_res"])
        if low_res_count > 0:
            penalty = min(20.0, low_res_count * 10.0)
            score -= penalty
            reasons.append(f"{low_res_count} page(s) are below minimum resolution ({settings.MIN_IMAGE_WIDTH}x{settings.MIN_IMAGE_HEIGHT}).")
            feedback_set.append("Document resolution is low. Please upload a higher resolution scan.")

        # Deduct for skewed pages
        skewed_count = sum(1 for p in page_diagnostics if p["is_skewed"])
        if skewed_count > 0:
            penalty = min(15.0, skewed_count * 8.0)
            score -= penalty
            reasons.append(f"{skewed_count} page(s) exhibit skew angle exceeding {settings.SKEW_ANGLE_THRESHOLD}°.")
            feedback_set.append("Document scan is tilted or skewed. Please upload an upright copy.")

        score = max(0.0, min(100.0, round(score, 1)))

        # Level mapping using configurable thresholds
        if score >= settings.QUALITY_SCORE_GOOD_THRESHOLD:
            level = QualityLevel.GOOD
        elif score >= settings.QUALITY_SCORE_ACCEPTABLE_THRESHOLD:
            level = QualityLevel.ACCEPTABLE
        elif score >= settings.QUALITY_SCORE_POOR_THRESHOLD:
            level = QualityLevel.POOR
        else:
            level = QualityLevel.UNUSABLE

        review_required = (level in [QualityLevel.POOR, QualityLevel.UNUSABLE]) or unreadable_count > 0

        if not feedback_set and level == QualityLevel.GOOD:
            feedback_set.append("Document quality is clear and verified for automated evaluation.")

        return score, level, review_required, reasons, feedback_set

    @classmethod
    def update_ocr_confidence_metrics(
        cls,
        db: Session,
        quality_result_id: uuid.UUID,
        avg_confidence: Optional[float],
        min_page_confidence: Optional[float] = None,
        page_confidences: Optional[Dict[int, float]] = None,
    ) -> None:
        """
        Updates DocumentQualityResult with final optical character recognition telemetry
        after the OCR stage executes.
        """
        qr = db.scalars(
            select(DocumentQualityResult)
            .options(joinedload(DocumentQualityResult.page_qualities))
            .where(DocumentQualityResult.id == quality_result_id)
        ).first()
        if not qr:
            return

        qr.average_ocr_confidence = avg_confidence
        qr.ocr_confidence = avg_confidence
        qr.min_page_ocr_confidence = min_page_confidence
        qr.updated_at = datetime.now(timezone.utc)

        # Update page OCR confidences if provided
        if page_confidences and qr.page_qualities:
            for pq in qr.page_qualities:
                if pq.page_number in page_confidences:
                    pq.ocr_confidence = page_confidences[pq.page_number]
                    pq.updated_at = datetime.now(timezone.utc)

        # If OCR confidence is very low (< MIN_OCR_CONFIDENCE), adjust quality level and review
        if avg_confidence is not None and avg_confidence < settings.MIN_OCR_CONFIDENCE:
            if qr.quality_level == QualityLevel.GOOD:
                qr.quality_level = QualityLevel.ACCEPTABLE
            qr.review_required = True
            low_ocr_reason = f"OCR confidence ({avg_confidence:.1%}) is below minimum threshold ({settings.MIN_OCR_CONFIDENCE:.1%})."
            if low_ocr_reason not in qr.review_reasons:
                qr.review_reasons.append(low_ocr_reason)

        db.commit()

    @classmethod
    def get_document_quality_for_bidder(
        cls,
        db: Session,
        current_user: User,
        bid_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> DocumentQualityResult:
        """
        Retrieves quality telemetry for a bidder's document with strict tenant isolation.
        Evaluates on-the-fly if quality record has not been generated yet.
        """
        _, bid, doc = _get_document_for_bidder(db, current_user, bid_id, document_id)

        qr = db.scalars(
            select(DocumentQualityResult)
            .options(joinedload(DocumentQualityResult.page_qualities))
            .where(DocumentQualityResult.document_id == doc.id)
        ).first()

        if qr:
            return qr

        # Generate quality assessment on-the-fly from storage binary
        if not storage_service.file_exists(doc.storage_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document binary file was not found in storage.",
            )

        file_bytes = storage_service.download_file(doc.storage_path)
        return cls.evaluate_document_quality(
            db=db,
            doc=doc,
            file_bytes=file_bytes,
            proc=doc.processing,
            user=current_user,
        )

    @classmethod
    def get_document_quality_for_procurement(
        cls,
        db: Session,
        current_user: User,
        tender_id: uuid.UUID,
        bid_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> DocumentQualityResult:
        """
        Retrieves full document quality diagnostic breakdown for Procurement Officers
        with tenant organization boundary checks.
        """
        if not current_user.profile_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User profile not configured.",
            )

        profile = db.scalars(
            select(Profile)
            .options(joinedload(Profile.role), joinedload(Profile.organization))
            .where(Profile.id == current_user.profile_id)
        ).first()

        if not profile or not profile.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User profile or role not found.",
            )

        role_name = profile.role.name.upper() if profile.role else ""
        if role_name not in ("PROCUREMENT_OFFICER", "ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Procurement document quality inspection is restricted to Procurement Officers and Admins.",
            )

        # Validate tender
        tender = db.scalars(
            select(Tender).where(Tender.id == tender_id, Tender.is_active == True)
        ).first()
        if not tender:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tender not found or inactive.",
            )

        if role_name != "ADMIN" and tender.organization_id != profile.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tender not found or access denied.",
            )

        # Validate bid and document
        doc = db.scalars(
            select(BidDocument)
            .options(
                joinedload(BidDocument.bid),
                joinedload(BidDocument.processing),
                joinedload(BidDocument.quality_result).joinedload(DocumentQualityResult.page_qualities),
            )
            .where(
                BidDocument.id == document_id,
                BidDocument.bid_id == bid_id,
            )
        ).first()

        if not doc or not doc.bid or doc.bid.tender_id != tender.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found for this tender and bid.",
            )

        if doc.quality_result:
            return doc.quality_result

        # Generate on-demand if missing
        if storage_service.file_exists(doc.storage_path):
            file_bytes = storage_service.download_file(doc.storage_path)
            return cls.evaluate_document_quality(
                db=db,
                doc=doc,
                file_bytes=file_bytes,
                proc=doc.processing,
                user=current_user,
            )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quality results not yet available and storage binary was not found.",
        )

    @classmethod
    def _record_quality_audit(
        cls,
        db: Session,
        doc: BidDocument,
        qr: DocumentQualityResult,
        user: Optional[User] = None,
    ) -> None:
        """Records immutable audit event for document quality diagnostics."""
        try:
            bid = doc.bid or db.scalars(select(Bid).where(Bid.id == doc.bid_id)).first()
            if not bid:
                return

            tender = bid.tender or db.scalars(select(Tender).where(Tender.id == bid.tender_id)).first()
            org_id = tender.organization_id if tender else bid.bidder_organization_id

            if qr.quality_level == QualityLevel.UNUSABLE:
                event_type = AuditEventType.DOCUMENT_QUALITY_UNUSABLE
            elif qr.review_required:
                event_type = AuditEventType.DOCUMENT_QUALITY_REVIEW_REQUIRED
            else:
                event_type = AuditEventType.DOCUMENT_QUALITY_CHECK_COMPLETED

            actor_user_id = user.id if user else None
            actor_profile_id = user.profile_id if user and user.profile_id else None
            actor_name = "System Document Quality Worker"
            actor_role = "SYSTEM"

            if user and user.profile:
                actor_name = user.profile.full_name
                actor_role = user.profile.role.name if user.profile.role else "USER"

            AuditService.record_event(
                db=db,
                event_dto=RecordAuditEventDTO(
                    organization_id=org_id,
                    tender_id=tender.id if tender else None,
                    bid_id=bid.id,
                    actor_user_id=actor_user_id,
                    actor_profile_id=actor_profile_id,
                    actor_name=actor_name,
                    actor_role=actor_role,
                    actor_source=AuditActorSource.SYSTEM if not user else AuditActorSource.HUMAN,
                    event_type=event_type,
                    entity_type=AuditEntityType.DOCUMENT_QUALITY_RESULT,
                    entity_id=qr.id,
                    action="DOCUMENT_QUALITY_EVALUATED",
                    summary=f"Evaluated quality for '{doc.original_filename}': {qr.quality_level} ({qr.quality_score}/100, review_required={qr.review_required}).",
                    metadata={
                        "document_id": str(doc.id),
                        "quality_score": qr.quality_score,
                        "quality_level": qr.quality_level,
                        "review_required": qr.review_required,
                        "page_count": qr.page_count,
                        "is_blurry": qr.is_blurry,
                        "has_blank_pages": qr.has_blank_pages,
                        "is_corrupted": qr.is_corrupted,
                    },
                ),
            )
            db.commit()

            # Part 12: Notification Center trigger for poor / unusable quality
            if qr.quality_level in (QualityLevel.POOR, QualityLevel.UNUSABLE) or qr.review_required:
                try:
                    from app.services.notification_service import NotificationService
                    NotificationService.notify_document_quality_review(db=db, doc=doc, qr=qr)
                except Exception as notif_err:
                    logger.debug("Failed to dispatch quality notification: %s", notif_err)
        except Exception as audit_err:
            logger.warning("Failed to record quality audit event for document %s: %s", doc.id, audit_err)
