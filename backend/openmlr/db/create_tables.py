"""Create (or recreate) all database tables from SQLAlchemy models."""

import sys
import asyncio
from .engine import engine
from .models import Base


async def create_all(drop_first: bool = False):
    async with engine.begin() as conn:
        if drop_first:
            await conn.run_sync(Base.metadata.drop_all)
            print("Dropped all tables.")
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Tables created.")


if __name__ == "__main__":
    fresh = "--fresh" in sys.argv
    if fresh:
        print("WARNING: dropping all tables and recreating from scratch.")
    asyncio.run(create_all(drop_first=fresh))
