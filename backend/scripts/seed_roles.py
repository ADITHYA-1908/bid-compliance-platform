import sys
import os
import logging

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.db.session import get_session_factory
from app.db.models.role import Role

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

INITIAL_ROLES = [
    {
        "name": "BIDDER",
        "description": "Bidder organization participating in GeM procurement and submitting bids",
    },
    {
        "name": "PROCUREMENT_OFFICER",
        "description": "Procurement / Buyer officer publishing tenders and evaluating bid compliance",
    },
    {
        "name": "ADMIN",
        "description": "Platform administrator with full system and user management oversight",
    },
]


def seed_roles() -> None:
    """
    Idempotent seeding script for foundational platform roles.
    Checks existing roles by name to avoid duplicate insertions.
    """
    session_factory = get_session_factory()
    db = session_factory()
    try:
        logger.info("Checking initial roles in database...")
        for role_data in INITIAL_ROLES:
            stmt = select(Role).where(Role.name == role_data["name"])
            existing_role = db.scalars(stmt).first()

            if existing_role:
                logger.info(f"Role '{role_data['name']}' already exists (ID: {existing_role.id}). Skipping.")
            else:
                new_role = Role(
                    name=role_data["name"],
                    description=role_data["description"],
                )
                db.add(new_role)
                db.commit()
                db.refresh(new_role)
                logger.info(f"Created role '{new_role.name}' (ID: {new_role.id}).")

        logger.info("Role seeding completed successfully.")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed roles: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_roles()
