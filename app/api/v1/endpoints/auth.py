import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionFactory
from app.core.security import create_access_token, hash_password, verify_password
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserRegisterRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    tenant_id: uuid.UUID,
    payload: UserRegisterRequest,
):
    """
    Onboard a user into a specific enterprise tenant.
    Validates tenant existence and prevents duplicate email registration within the tenant.
    """
    async with AsyncSessionFactory() as session:
        async with session.begin():
            # 1. Verify that the target tenant exists and is active
            tenant = await session.get(Tenant, tenant_id)
            if not tenant or not tenant.is_active:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Enterprise tenant not found or inactive",
                )

            # 2. Check if the user already exists within this tenant
            query = select(User).where(User.tenant_id ==
                                       tenant_id, User.email == payload.email)
            existing_user = (await session.execute(query)).scalar_one_or_none()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email already exists in this tenant",
                )

            # 3. Create the user with a bcrypt hashed password
            new_user = User(
                tenant_id=tenant_id,
                email=payload.email,
                hashed_password=hash_password(payload.password),
                role=payload.role,
            )
            session.add(new_user)
            await session.flush()
            await session.refresh(new_user)
            return new_user


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    """
    Authenticates a user and issues a cryptographically signed JWT
    embedding tenant_id and role claims.
    """
    async with AsyncSessionFactory() as session:
        # Search for user across active tenants
        query = select(User).join(Tenant).where(
            User.email == payload.email,
            Tenant.is_active.is_(True)
        )
        user = (await session.execute(query)).scalar_one_or_none()

        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Mint the signed JWT
        token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = create_access_token(
            subject=str(user.id),
            tenant_id=str(user.tenant_id),
            role=user.role,
            expires_delta=token_expires,
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
