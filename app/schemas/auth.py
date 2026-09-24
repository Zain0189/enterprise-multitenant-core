import uuid
from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    """Schema returned upon successful authentication containing the signed JWT."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    """Schema for user authentication."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="User plain password")


class UserRegisterRequest(BaseModel):
    """Schema for onboarding a new user within a tenant."""
    email: EmailStr
    password: str = Field(..., min_length=8,
                          description="Minimum 8-character password")
    role: str = Field(default="viewer", pattern="^(admin|analyst|viewer)$")


class UserResponse(BaseModel):
    """Safe public representation of a user (excludes hashed_password)."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: EmailStr
    role: str

    model_config = {"from_attributes": True}
