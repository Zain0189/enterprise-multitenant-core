import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    # UUID Primary Key: Non-guessable, globally unique
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Human-readable organization name (e.g., "Acme Corp")
    name: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        nullable=False
    )

    # URL-friendly identifier (e.g., "acme-corp")
    slug: Mapped[str] = mapped_column(
        String(60),
        unique=True,
        nullable=False,
        index=True
    )

    # Soft toggle to deactivate an entire enterprise organization instantly
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    # Audit timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    documents: Mapped[list["EnterpriseDocument"]] = relationship(
        "EnterpriseDocument",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
