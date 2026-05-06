"""Database connection and session management via SQLAlchemy async."""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

_DATABASE_URL = (
    f"postgresql+asyncpg://{os.getenv('POSTGRES_USER', 'spb_user')}"
    f":{os.getenv('POSTGRES_PASSWORD', 'changeme')}"
    f"@{os.getenv('POSTGRES_HOST', 'localhost')}"
    f":{os.getenv('POSTGRES_PORT', '5432')}"
    f"/{os.getenv('POSTGRES_DB', 'synthetic_persona')}"
)

engine = create_async_engine(_DATABASE_URL, echo=False, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_async_session() -> AsyncSession:
    """Return a raw async session for use as an async context manager.

    Use this outside of FastAPI dependency injection (e.g. WebSocket handlers,
    background tasks, Airflow operators that import the ORM layer).

        async with get_async_session() as db:
            result = await db.execute(...)
    """
    return AsyncSessionLocal()
