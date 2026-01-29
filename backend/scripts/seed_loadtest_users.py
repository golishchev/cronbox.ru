#!/usr/bin/env python3
"""Seed script to create load test users."""

import asyncio
import secrets
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.database import AsyncSessionLocal
from app.models.user import User
from app.models.workspace import Workspace

# Same users as in locustfile.py
LOAD_TEST_USERS = [
    {"email": "loadtest1@example.com", "password": "LoadTest123!", "name": "Load Test User 1"},
    {"email": "loadtest2@example.com", "password": "LoadTest123!", "name": "Load Test User 2"},
    {"email": "loadtest3@example.com", "password": "LoadTest123!", "name": "Load Test User 3"},
    {"email": "loadtest4@example.com", "password": "LoadTest123!", "name": "Load Test User 4"},
    {"email": "loadtest5@example.com", "password": "LoadTest123!", "name": "Load Test User 5"},
]


async def seed_loadtest_users():
    """Create load test users with verified emails and workspaces."""
    async with AsyncSessionLocal() as db:
        for user_data in LOAD_TEST_USERS:
            # Check if user exists
            result = await db.execute(select(User).where(User.email == user_data["email"]))
            existing_user = result.scalar_one_or_none()

            if existing_user:
                # Update existing user to ensure email is verified
                existing_user.email_verified = True
                existing_user.is_active = True
                print(f"Updated user: {user_data['email']} (email_verified=True)")
                user = existing_user
            else:
                # Create new user
                user = User(
                    email=user_data["email"],
                    password_hash=get_password_hash(user_data["password"]),
                    name=user_data["name"],
                    email_verified=True,
                    is_active=True,
                )
                db.add(user)
                await db.flush()  # Get user ID
                print(f"Created user: {user_data['email']}")

            # Check if user has a workspace
            result = await db.execute(select(Workspace).where(Workspace.owner_id == user.id))
            existing_workspace = result.scalar_one_or_none()

            if not existing_workspace:
                # Create workspace for user
                workspace = Workspace(
                    name="Load Test Workspace",
                    slug=f"loadtest-{user_data['email'].split('@')[0]}",
                    owner_id=user.id,
                    webhook_secret=secrets.token_urlsafe(32),
                    default_timezone="Europe/Moscow",
                )
                db.add(workspace)
                print(f"  Created workspace for {user_data['email']}")

        await db.commit()
        print("\nAll load test users seeded successfully!")


async def cleanup_loadtest_users():
    """Remove all load test users and their data."""
    async with AsyncSessionLocal() as db:
        emails = [u["email"] for u in LOAD_TEST_USERS]
        result = await db.execute(select(User).where(User.email.in_(emails)))
        users = result.scalars().all()

        for user in users:
            await db.delete(user)
            print(f"Deleted user: {user.email}")

        await db.commit()
        print("\nAll load test users cleaned up!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage load test users")
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove load test users instead of creating them",
    )
    args = parser.parse_args()

    if args.cleanup:
        asyncio.run(cleanup_loadtest_users())
    else:
        asyncio.run(seed_loadtest_users())
