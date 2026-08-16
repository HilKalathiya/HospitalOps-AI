"""
HospitalOps AI — Seed Demo Users.

Populates the database with initial demo users for the 3 core roles:
- ADMIN
- DOCTOR
- OPERATIONS_MANAGER

Usage:
    python backend/scripts/seed_demo_users.py
"""

import asyncio
import logging
import sys
import uuid
from pathlib import Path

# Add the parent directory to sys.path so we can import 'app'
sys.path.append(str(Path(__file__).resolve().parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.models.user import Role, UserCreate
from app.repositories.users import UserRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_users() -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_database]
    user_repo = UserRepository(db)

    # Ensure indexes first
    await user_repo.ensure_indexes()

    users_to_create = [
        UserCreate(
            email="admin@hospitalops.local",
            name="System Administrator",
            password="adminpassword123",
            role=Role.ADMIN,
        ),
        UserCreate(
            email="doctor@hospitalops.local",
            name="Dr. Sarah Chen",
            password="doctorpassword123",
            role=Role.DOCTOR,
            department_id="ER",
        ),
        UserCreate(
            email="manager@hospitalops.local",
            name="James Wilson",
            password="managerpassword123",
            role=Role.OPERATIONS_MANAGER,
        ),
    ]

    for user_data in users_to_create:
        existing = await user_repo.find_by_email(user_data.email)
        if existing:
            logger.info("User %s already exists. Skipping.", user_data.email)
            continue

        # Convert to UserDocument
        from app.models.user import UserDocument

        doc = UserDocument(
            user_id=str(uuid.uuid4()),
            email=user_data.email,
            name=user_data.name,
            password_hash=get_password_hash(user_data.password),
            role=user_data.role,
            department_id=user_data.department_id,
        )
        await user_repo.create_user(doc)
        logger.info("Created user: %s (%s)", user_data.name, user_data.role.value)

    logger.info("Demo users seeded successfully.")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_users())
