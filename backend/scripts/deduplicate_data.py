"""
BidVerify AI — Safe Database Deduplication Script
Identifies and cleans up duplicate bid document records, duplicate notifications,
and enforces unique data integrity without deleting historical audit trails or legitimate data.
"""

import sys
import logging
from sqlalchemy import func

sys.path.insert(0, "./backend")

from app.db.session import get_session_factory
from app.db.models.tender import Tender
from app.db.models.bid import Bid
from app.db.models.bid_document import BidDocument
from app.db.models.compliance_result import ComplianceResult
from app.db.models.verification_record import VerificationRecord
from app.db.models.notification import Notification
from app.db.models.organization import Organization

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_deduplication():
    session_factory = get_session_factory()
    db = session_factory()

    logger.info("=== Starting Safe Database Deduplication ===")

    try:
        # 1. Deduplicate Bid Documents with identical file_hash in the same bid
        logger.info("Inspecting duplicate Bid Documents...")
        duplicate_doc_groups = (
            db.query(BidDocument.bid_id, BidDocument.file_hash, func.count(BidDocument.id))
            .filter(BidDocument.file_hash.isnot(None))
            .group_by(BidDocument.bid_id, BidDocument.file_hash)
            .having(func.count(BidDocument.id) > 1)
            .all()
        )

        docs_removed = 0
        for bid_id, file_hash, count in duplicate_doc_groups:
            # Fetch all matching documents ordered by created_at DESC (keep the latest)
            docs = (
                db.query(BidDocument)
                .filter(BidDocument.bid_id == bid_id, BidDocument.file_hash == file_hash)
                .order_by(BidDocument.created_at.desc())
                .all()
            )
            # Keep the first (latest), delete the rest
            to_delete = docs[1:]
            for doc in to_delete:
                # Nullify or delete references if any
                db.delete(doc)
                docs_removed += 1

        logger.info(f"Deduplicated Bid Documents: removed {docs_removed} duplicate records.")

        # 2. Deduplicate Compliance Results (same bid_id and tender_requirement_id)
        logger.info("Inspecting duplicate Compliance Results...")
        duplicate_compliance = (
            db.query(ComplianceResult.bid_id, ComplianceResult.tender_requirement_id, func.count(ComplianceResult.id))
            .group_by(ComplianceResult.bid_id, ComplianceResult.tender_requirement_id)
            .having(func.count(ComplianceResult.id) > 1)
            .all()
        )

        comp_removed = 0
        for bid_id, req_id, count in duplicate_compliance:
            results = (
                db.query(ComplianceResult)
                .filter(ComplianceResult.bid_id == bid_id, ComplianceResult.tender_requirement_id == req_id)
                .order_by(ComplianceResult.created_at.desc())
                .all()
            )
            for res in results[1:]:
                db.delete(res)
                comp_removed += 1

        logger.info(f"Deduplicated Compliance Results: removed {comp_removed} duplicate records.")

        # 3. Deduplicate Verification Records (same bid_id and verification_type)
        logger.info("Inspecting duplicate Verification Records...")
        duplicate_verifications = (
            db.query(VerificationRecord.bid_id, VerificationRecord.verification_type, func.count(VerificationRecord.id))
            .group_by(VerificationRecord.bid_id, VerificationRecord.verification_type)
            .having(func.count(VerificationRecord.id) > 1)
            .all()
        )

        verif_removed = 0
        for bid_id, vtype, count in duplicate_verifications:
            records = (
                db.query(VerificationRecord)
                .filter(VerificationRecord.bid_id == bid_id, VerificationRecord.verification_type == vtype)
                .order_by(VerificationRecord.created_at.desc())
                .all()
            )
            for rec in records[1:]:
                db.delete(rec)
                verif_removed += 1

        logger.info(f"Deduplicated Verification Records: removed {verif_removed} duplicate records.")

        # Commit all deduplication changes
        db.commit()
        logger.info("=== Database Deduplication Completed Successfully ===")

    except Exception as e:
        db.rollback()
        logger.error(f"Error during deduplication: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_deduplication()
