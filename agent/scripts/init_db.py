#!/usr/bin/env python3
"""Create ORM tables and seed demo clinic data.

Replaces the old SQL migration files (001_schema.sql / 002_seed.sql).

Run from the agent folder:
  .venv/bin/python scripts/init_db.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from clinic.orm.engine import create_tables, get_async_engine  # noqa: E402
from clinic.orm.seed import seed_database  # noqa: E402
from clinic.orm.tables import (  # noqa: E402
    Appointment,
    BlockedPeriod,
    Clinic,
    Doctor,
    DoctorSchedule,
    Patient,
    Specialty,
)
from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402


def load_dsn() -> str:
    import os

    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        raise SystemExit("DATABASE_URL not found in agent/.env")
    return dsn


async def main() -> None:
    dsn = load_dsn()
    engine = get_async_engine(dsn)

    print("Creating tables (SQLAlchemy ORM)...")
    await create_tables(engine)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        async with session.begin():
            seeded = await seed_database(session)
        print("Seeded demo data." if seeded else "Demo data already present, skipped.")

        async with session.begin():
            counts = {
                "clinics": await session.scalar(select(func.count()).select_from(Clinic)),
                "specialties": await session.scalar(select(func.count()).select_from(Specialty)),
                "doctors": await session.scalar(select(func.count()).select_from(Doctor)),
                "doctor_schedules": await session.scalar(select(func.count()).select_from(DoctorSchedule)),
                "blocked_periods": await session.scalar(select(func.count()).select_from(BlockedPeriod)),
                "patients": await session.scalar(select(func.count()).select_from(Patient)),
                "appointments": await session.scalar(select(func.count()).select_from(Appointment)),
            }
        print("\nRow counts:")
        for table, count in counts.items():
            print(f"  {table:18} {count}")

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
