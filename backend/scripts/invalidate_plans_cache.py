#!/usr/bin/env python3
"""Script to invalidate plans cache in Redis."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.redis import redis_client
from app.services.billing import billing_service


async def main():
    """Invalidate plans cache."""
    try:
        # Initialize Redis connection
        print("Connecting to Redis...")
        await redis_client.initialize()

        # Invalidate cache
        print("Invalidating plans cache...")
        await billing_service.invalidate_plans_cache()
        print("✓ Plans cache invalidated successfully")

    finally:
        # Close Redis connection
        await redis_client.close()


if __name__ == "__main__":
    asyncio.run(main())
