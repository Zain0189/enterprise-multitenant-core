from datetime import datetime, timedelta, timezone
from typing import Any
import jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing configuration using standard bcrypt algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against an existing bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    tenant_id: str,
    role: str,
    expires_delta: timedelta | None = None
) -> str:
    """
    Generates a cryptographically signed JWT containing claims for:
    - sub: The unique User ID
    - tenant_id: The verified organization boundary
    - role: The Role-Based Access Control identity ('admin', 'analyst', 'viewer')
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    claims: dict[str, Any] = {
        "sub": str(subject),
        "tenant_id": str(tenant_id),
        "role": str(role),
        "iat": now,
        "exp": expire,
    }

    encoded_jwt = jwt.encode(
        claims,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decodes and cryptographically validates a JWT token.
    Raises jwt.PyJWTError if expired, malformed, or signature is invalid.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
