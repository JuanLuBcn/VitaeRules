"""Development seed script for populating test data."""

import asyncio
from pathlib import Path

from app.config import get_settings
from app.tracing import get_tracer


async def seed_test_data():
    """Seed the database with test data for development."""
    settings = get_settings()
    tracer = get_tracer()

    tracer.info("Seeding test data...")

    # TODO: Implement seeding logic
    # - Create sample users
    # - Create sample memory items
    # - Create sample tasks and lists

    tracer.info("Test data seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_test_data())
