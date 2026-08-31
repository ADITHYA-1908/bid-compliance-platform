import sys
import os
import logging

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_session_factory
from app.db.models.role import Role
from app.db.models.organization import Organization
from app.db.models.profile import Profile
from app.db.models.user import User
from app.core.security import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TEST_USERS = [
    {
        "email": "bidder@test.local",
        "full_name": "Verified Bidder User",
        "role_name": "BIDDER",
        "organization_name": "ABC Infra Technologies Ltd",
        "organization_type": "Private Vendor",
        "password": "TestPassword123!",
    },
    {
        "email": "procurement@test.local",
        "full_name": "Executive Procurement Officer",
        "role_name": "PROCUREMENT_OFFICER",
        "organization_name": "Ministry of Electronics & IT",
        "organization_type": "Government Ministry",
        "password": "TestPassword123!",
    },
    {
        "email": "admin@test.local",
        "full_name": "System Administrator",
        "role_name": "ADMIN",
        "organization_name": "GeM Platform Administration",
        "organization_type": "Platform Oversight",
        "password": "TestPassword123!",
    },
]


def create_test_users() -> None:
    """
    Idempotently provisions designated test accounts for each system role:
    - BIDDER (bidder@test.local)
    - PROCUREMENT_OFFICER (procurement@test.local)
    - ADMIN (admin@test.local)
    """
    session_factory = get_session_factory()
    db = session_factory()

    try:
        logger.info("Provisioning Part 1D test accounts...")

        # 1. Fetch available roles
        roles = {r.name: r for r in db.scalars(select(Role)).all()}
        for req_role in ["BIDDER", "PROCUREMENT_OFFICER", "ADMIN"]:
            if req_role not in roles:
                raise ValueError(f"Required role '{req_role}' not found in database. Run seed_roles.py first.")

        for item in TEST_USERS:
            email = item["email"].lower()
            role = roles[item["role_name"]]

            # Check if user exists
            stmt = select(User).where(User.email == email).options(
                selectinload(User.profile).selectinload(Profile.role),
                selectinload(User.profile).selectinload(Profile.organization),
            )
            existing_user = db.scalars(stmt).first()

            if existing_user:
                logger.info(f"Test user '{email}' already exists (ID: {existing_user.id}, Role: {existing_user.profile.role.name}). Skipping.")
                continue

            # Check or create Organization
            org = db.scalars(
                select(Organization).where(Organization.name == item["organization_name"])
            ).first()
            if not org:
                org = Organization(
                    name=item["organization_name"],
                    organization_type=item["organization_type"],
                    is_active=True,
                )
                db.add(org)
                db.flush()

            # Check or create Profile
            profile = db.scalars(select(Profile).where(Profile.email == email)).first()
            if not profile:
                profile = Profile(
                    full_name=item["full_name"],
                    email=email,
                    role_id=role.id,
                    organization_id=org.id,
                    is_active=True,
                )
                db.add(profile)
                db.flush()

            # Create User
            user = User(
                email=email,
                password_hash=hash_password(item["password"]),
                profile_id=profile.id,
                is_active=True,
            )
            db.add(user)
            db.commit()
            logger.info(f"Created test user '{email}' with role '{role.name}' (User ID: {user.id}).")

        logger.info("All Part 1D test accounts are ready.")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create test users: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_test_users()
