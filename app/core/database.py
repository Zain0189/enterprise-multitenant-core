from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


class Base(DeclarativeBase):
    pass


# Use NullPool in development/testing to avoid Windows event-loop socket reuse conflicts
engine = create_async_engine(
    settings.APP_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_tenant_db_session(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Yields a database session with the active tenant ID locked into

    PostgreSQL's session variables via set_config(..., is_local=true).
    """
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
                {"tenant_id": str(tenant_id)},
            )
            yield session
