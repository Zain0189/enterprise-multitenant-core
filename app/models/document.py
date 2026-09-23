import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EnterpriseDocument(Base):
    __tablename__ = "enterprise_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Foreign Key ensuring the document strictly belongs to a specific tenant
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # PostgreSQL native JSONB for flexible enterprise metadata (tags, source links, vector IDs)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",  # column name in database
        JSONB,
        server_default="{}",
        nullable=False
    )

    # Optional track of which specific user authored the document
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="documents"
    )
    author: Mapped["User | None"] = relationship(
        "User",
        back_populates="created_documents"
    )
