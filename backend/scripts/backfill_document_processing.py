"""
Idempotent Backfill Script for Part 4A: Document Processing Records
Provisions QUEUED DocumentProcessing records for any historical BidDocument
instances created prior to Part 4A deployment.
"""

import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import get_session_factory
from app.services.document_processing_service import backfill_missing_processing_records


def run_backfill():
    print("Starting Part 4A DocumentProcessing backfill...")
    session_factory = get_session_factory()
    db = session_factory()
    try:
        created_count = backfill_missing_processing_records(db)
        print(f"Backfill complete. Provisioned {created_count} new DocumentProcessing records.")
    except Exception as e:
        print(f"Error during backfill: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_backfill()
