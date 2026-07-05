"""Async SQLAlchemy engine and session factory."""
from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from .tables import Base


def sanitize_dsn(dsn: str) -> str:
    """Strip libpq-only query params (e.g. channel_binding) that asyncpg rejects."""
    return re.sub(r"\?.*$", "", dsn)


def to_async_url(dsn: str) -> str:
    dsn = sanitize_dsn(dsn)
    if dsn.startswith("postgresql+asyncpg://"):
        return dsn
    if dsn.startswith("postgresql://"):
        return dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    if dsn.startswith("postgres://"):
        return dsn.replace("postgres://", "postgresql+asyncpg://", 1)
    return dsn


def get_async_engine(dsn: str) -> AsyncEngine:
    return create_async_engine(to_async_url(dsn), echo=False, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
