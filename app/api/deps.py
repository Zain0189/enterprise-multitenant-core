import uuid
from typing import AsyncGenerator
from dataclasses import dataclass
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_access_token
from app.core.database import get_tenant_db_session

# OAuth2 scheme: tells FastAPI to look for the "Authorization: Bearer <token>" header
# and provides interactive token authentication in Swagger/OpenAPI docs
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@dataclass(frozen=True)
class SecurityContext:
    """
    Immutable request context carrying cryptographically verified
    tenant identity and Role-Based Access Control (RBAC) claims.
    """
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: str


async def get_current_user_context(
    token: str = Depends(oauth2_scheme)
) -> SecurityContext:
    """
    Extracts and cryptographically validates the JWT token from the Authorization header.
    Returns an immutable SecurityContext object containing tenant_id, user_id, and role.
    Raises HTTP 401 Unauthorized if the token is missing, expired, or tampered with.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate enterprise credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id_str: str | None = payload.get("sub")
        tenant_id_str: str | None = payload.get("tenant_id")
        role: str | None = payload.get("role")

        if not user_id_str or not tenant_id_str or not role:
            raise credentials_exception

        return SecurityContext(
            user_id=uuid.UUID(user_id_str),
            tenant_id=uuid.UUID(tenant_id_str),
            role=role,
        )

    except (jwt.PyJWTError, ValueError):
        # Catches expired tokens, signature mismatches, or malformed UUID strings
        raise credentials_exception


async def get_tenant_db(
    context: SecurityContext = Depends(get_current_user_context)
) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI database dependency.
    Automatically obtains the verified tenant_id from get_current_user_context,
    configures PostgreSQL session variables via get_tenant_db_session,
    and yields an active database session strictly locked to that tenant's RLS boundary.
    """
    async with get_tenant_db_session(str(context.tenant_id)) as session:
        yield session
