#!/usr/bin/env python3
"""Seed script to create default plans."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.models.plan import Plan

PLANS = [
    {
        "name": "free",
        "display_name": "Free",
        "description": "Бесплатный тариф для знакомства с сервисом",
        "price_monthly": 0,
        "price_yearly": 0,
        "max_cron_tasks": 3,
        "max_delayed_tasks_per_month": 50,
        "max_workspaces": 1,
        "max_execution_history_days": 3,
        "min_cron_interval_minutes": 15,
        "telegram_notifications": False,
        "email_notifications": False,
        "webhook_callbacks": False,
        "custom_headers": True,
        "retry_on_failure": False,
        # Task Chains - not available on free plan
        "max_task_chains": 0,
        "max_chain_steps": 5,
        "chain_variable_substitution": False,
        "min_chain_interval_minutes": 15,
        # Heartbeat monitors
        "max_heartbeats": 1,
        "min_heartbeat_interval_minutes": 60,
        # SSL monitors
        "max_ssl_monitors": 1,
        # Launch policy (overlap prevention)
        "overlap_prevention_enabled": False,
        "max_queue_size": 0,
        "is_active": True,
        "is_public": True,
        "sort_order": 0,
    },
    {
        "name": "pro",
        "display_name": "Pro",
        "description": "Для разработчиков и небольших проектов",
        "price_monthly": 49000,  # 490 rubles in kopeks
        "price_yearly": 490000,  # 4900 rubles in kopeks
        "max_cron_tasks": 25,
        "max_delayed_tasks_per_month": 500,
        "max_workspaces": 3,
        "max_execution_history_days": 30,
        "min_cron_interval_minutes": 1,
        "telegram_notifications": True,
        "email_notifications": True,
        "webhook_callbacks": True,
        "custom_headers": True,
        "retry_on_failure": True,
        # Task Chains
        "max_task_chains": 5,
        "max_chain_steps": 5,
        "chain_variable_substitution": True,
        "min_chain_interval_minutes": 15,
        # Heartbeat monitors
        "max_heartbeats": 10,
        "min_heartbeat_interval_minutes": 5,
        # SSL monitors
        "max_ssl_monitors": 10,
        # Launch policy (overlap prevention)
        "overlap_prevention_enabled": True,
        "max_queue_size": 10,
        "is_active": True,
        "is_public": True,
        "sort_order": 1,
    },
    {
        "name": "max",
        "display_name": "Max",
        "description": "Для команд и серьёзных проектов",
        "price_monthly": 149000,  # 1490 rubles in kopeks
        "price_yearly": 1490000,  # 14900 rubles in kopeks
        "max_cron_tasks": 100,
        "max_delayed_tasks_per_month": 5000,
        "max_workspaces": 10,
        "max_execution_history_days": 90,
        "min_cron_interval_minutes": 1,
        "telegram_notifications": True,
        "email_notifications": True,
        "webhook_callbacks": True,
        "custom_headers": True,
        "retry_on_failure": True,
        # Task Chains
        "max_task_chains": 20,
        "max_chain_steps": 15,
        "chain_variable_substitution": True,
        "min_chain_interval_minutes": 1,
        # Heartbeat monitors
        "max_heartbeats": 50,
        "min_heartbeat_interval_minutes": 1,
        # SSL monitors
        "max_ssl_monitors": 50,
        # Launch policy (overlap prevention)
        "overlap_prevention_enabled": True,
        "max_queue_size": 100,
        "is_active": True,
        "is_public": True,
        "sort_order": 2,
    },
]


async def seed_plans():
    """Create or update plans in the database."""
    async with AsyncSessionLocal() as db:
        for plan_data in PLANS:
            # Check if plan exists
            result = await db.execute(select(Plan).where(Plan.name == plan_data["name"]))
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing plan
                for key, value in plan_data.items():
                    if key != "name":  # Don't update name
                        setattr(existing, key, value)
                print(f"Updated plan: {plan_data['name']}")
            else:
                # Create new plan
                plan = Plan(**plan_data)
                db.add(plan)
                print(f"Created plan: {plan_data['name']}")

        await db.commit()
        print("\nAll plans seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_plans())
