import uuid
from typing import AsyncGenerator
import pytest
from sqlalchemy import delete
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.models.document import EnterpriseDocument
from app.models.tenant import Tenant
from app.models.user import User

# Admin engine: connects as 'postgres' to manage seed data without RLS restrictions
admin_engine = create_async_engine(
    settings.ADMIN_DATABASE_URL.replace("psycopg2", "asyncpg"),
    echo=False,
    poolclass=NullPool,
)

AdminSessionFactory = async_sessionmaker(
    bind=admin_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def tenant_alpha_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture(scope="session")
def tenant_beta_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture(scope="function")
async def seed_test_tenants(
    tenant_alpha_id: uuid.UUID, tenant_beta_id: uuid.UUID
) -> AsyncGenerator[None, None]:
    async with AdminSessionFactory() as session:
        async with session.begin():
            await session.execute(delete(EnterpriseDocument))
            await session.execute(delete(User))
            await session.execute(delete(Tenant))

            alpha = Tenant(
                id=tenant_alpha_id,
                name="Acme Corporation",
                slug=f"acme-{uuid.uuid4().hex[:6]}",
                is_active=True,
            )

            beta = Tenant(
                id=tenant_beta_id,
                name="Globex Corporation",
                slug=f"globex-{uuid.uuid4().hex[:6]}",
                is_active=True,
            )

            session.add_all([alpha, beta])

    yield

    async with AdminSessionFactory() as session:
        async with session.begin():
            await session.execute(delete(EnterpriseDocument))
            await session.execute(delete(User))
            await session.execute(delete(Tenant))
