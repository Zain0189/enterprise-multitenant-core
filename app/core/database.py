from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# 1. Base class for all ORM models
class Base(DeclarativeBase):
    pass


# 2. Async engine using the least-privilege application role (app_user)
engine = create_async_engine(
    settings.APP_DATABASE_URL,
    echo=False,  # Set to True only when debugging raw SQL queries
    pool_size=10,  # Max persistent connections in the pool
    max_overflow=20,  # Temporary connections during traffic spikes
    pool_pre_ping=True,  # Verifies connection health before handing it to a query
)

# 3. Factory for producing individual async sessions
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# 4. Tenant-scoped database session manager
@asynccontextmanager
async def get_tenant_db_session(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Yields a database session with the active tenant ID locked into

    PostgreSQL's session variables.

    This ensures Row-Level Security (RLS) policies filter out all other tenants'
    data.
    """
    async with AsyncSessionFactory() as session:
        async with session.begin():
            # SET LOCAL restricts the variable's scope to the current transaction.
            # Once the transaction commits or rolls back, the variable resets.
            await session.execute(
                text("SET LOCAL app.current_tenant_id = :tenant_id"),
                {"tenant_id": str(tenant_id)},
            )
            yield session
