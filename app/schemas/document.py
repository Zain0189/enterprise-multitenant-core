import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    """Payload required to ingest a new document."""
    title: str = Field(..., min_length=1, max_length=255,
                       description="Document title")
    content: str = Field(..., min_length=1,
                         description="Document body or text payload")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary JSON metadata")


class DocumentUpdate(BaseModel):
    """Payload for updating an existing document (all fields optional)."""
    title: str | None = Field(None, min_length=1, max_length=255)
    content: str | None = Field(None, min_length=1)
    metadata: dict[str, Any] | None = None


class DocumentResponse(BaseModel):
    """Contract returned to enterprise clients for document queries."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    content: str
    metadata: dict[str, Any] = Field(alias="metadata_")
    created_by: uuid.UUID | None
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }
