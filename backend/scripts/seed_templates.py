#!/usr/bin/env python3
"""Seed script to create default notification templates."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import AsyncSessionLocal
from app.services.template_service import template_service


async def seed_templates():
    """Create default notification templates in the database."""
    async with AsyncSessionLocal() as db:
        created = await template_service.seed_default_templates(db)
        if created > 0:
            print(f"Created {created} notification templates")
        else:
            print("All notification templates already exist")


if __name__ == "__main__":
    asyncio.run(seed_templates())
