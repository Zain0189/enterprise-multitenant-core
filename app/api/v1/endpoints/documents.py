import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SecurityContext, get_tenant_db
from app.api.permissions import (
    require_admin,
    require_analyst_or_above,
    require_any_authenticated_user,
)
from app.models.document import EnterpriseDocument
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate

router = APIRouter(prefix="/documents", tags=["Enterprise Documents"])


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreate,
    context: SecurityContext = Depends(require_analyst_or_above),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    Ingest a new enterprise document.
    Enforces RBAC: Requires 'analyst' or 'admin' role.
    Tenant boundary is automatically guaranteed by get_tenant_db and RLS.
    """
    new_doc = EnterpriseDocument(
        tenant_id=context.tenant_id,
        title=payload.title,
        content=payload.content,
        metadata_=payload.metadata,
        created_by=context.user_id,
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    return new_doc


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    context: SecurityContext = Depends(require_any_authenticated_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    List all documents for the authenticated tenant.
    Accessible to all roles (admin, analyst, viewer).
    RLS guarantees zero data leakage across tenants even with a blanket SELECT.
    """
    result = await db.execute(select(EnterpriseDocument))
    return result.scalars().all()


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    context: SecurityContext = Depends(require_any_authenticated_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    Retrieve a specific document by UUID.
    Returns 404 if the document does not exist OR belongs to another tenant.
    """
    doc = await db.get(EnterpriseDocument, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return doc


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    context: SecurityContext = Depends(require_analyst_or_above),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    Update document fields partially.
    Requires 'analyst' or 'admin' role.
    """
    doc = await db.get(EnterpriseDocument, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if payload.title is not None:
        doc.title = payload.title
    if payload.content is not None:
        doc.content = payload.content
    if payload.metadata is not None:
        doc.metadata_ = payload.metadata

    await db.commit()
    await db.refresh(doc)
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    context: SecurityContext = Depends(require_admin),
    db: AsyncSession = Depends(get_tenant_db),
):
    """
    Permanently delete an enterprise document.
    Enforces strict RBAC: Admin role required.
    """
    doc = await db.get(EnterpriseDocument, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    await db.delete(doc)
    await db.commit()
    return None
