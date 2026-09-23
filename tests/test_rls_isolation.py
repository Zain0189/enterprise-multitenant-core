import uuid
import pytest
from sqlalchemy import select, update, delete
from sqlalchemy.exc import DBAPIError

from app.core.database import get_tenant_db_session
from app.models.document import EnterpriseDocument


@pytest.mark.asyncio
async def test_tenant_cannot_read_other_tenant_documents(
    seed_test_tenants,
    tenant_alpha_id: uuid.UUID,
    tenant_beta_id: uuid.UUID,
):
    """
    ATTACK VECTOR 1: Unscoped Data Leakage
    Tenant Alpha creates a sensitive document.
    Tenant Beta queries the documents table with NO WHERE clause.
    VERIFICATION: Tenant Beta must receive an empty result set.
    """
    # 1. Tenant Alpha connects and inserts a confidential document
    async with get_tenant_db_session(str(tenant_alpha_id)) as session:
        doc = EnterpriseDocument(
            tenant_id=tenant_alpha_id,
            title="Alpha Secret Strategic Acquisition",
            content="Top-secret roadmap for Q4.",
            metadata_={"confidentiality": "strictly_internal"}
        )
        session.add(doc)
        await session.commit()

    # 2. Tenant Beta connects and runs a blanket SELECT query (no tenant filter)
    async with get_tenant_db_session(str(tenant_beta_id)) as session:
        query = select(EnterpriseDocument)
        result = await session.execute(query)
        beta_visible_docs = result.scalars().all()

        # RLS MUST ensure Beta sees 0 rows from Alpha
        assert len(
            beta_visible_docs) == 0, "Data leakage! Tenant Beta saw Tenant Alpha documents."

    # 3. Confirm Tenant Alpha can still read their own document
    async with get_tenant_db_session(str(tenant_alpha_id)) as session:
        query = select(EnterpriseDocument)
        result = await session.execute(query)
        alpha_visible_docs = result.scalars().all()

        assert len(alpha_visible_docs) == 1
        assert alpha_visible_docs[0].title == "Alpha Secret Strategic Acquisition"


@pytest.mark.asyncio
async def test_tenant_cannot_spoof_insertion_for_another_tenant(
    seed_test_tenants,
    tenant_alpha_id: uuid.UUID,
    tenant_beta_id: uuid.UUID,
):
    """
    ATTACK VECTOR 2: Tenant Spoofing / Malicious Injection
    Tenant Beta connects with their own session, but crafts an INSERT payload
    explicitly setting tenant_id to Tenant Alpha's UUID.
    VERIFICATION: PostgreSQL RLS WITH CHECK policy must reject the insert with an error.
    """
    async with get_tenant_db_session(str(tenant_beta_id)) as session:
        spoofed_doc = EnterpriseDocument(
            tenant_id=tenant_alpha_id,  # Maliciously injecting Alpha's tenant_id
            title="Spoofed Forged Record",
            content="Trying to inject rogue data into Alpha's tenant boundary.",
            metadata_={"status": "malicious"}
        )
        session.add(spoofed_doc)

        # Database engine must reject this commit due to RLS WITH CHECK clause
        with pytest.raises(DBAPIError) as exc_info:
            await session.commit()

        # Verify the underlying database error confirms an RLS check violation
        assert "row-level security policy" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_tenant_cannot_mutate_or_delete_other_tenant_data(
    seed_test_tenants,
    tenant_alpha_id: uuid.UUID,
    tenant_beta_id: uuid.UUID,
):
    """
    ATTACK VECTOR 3: Cross-Tenant Data Tampering / Destruction
    Tenant Alpha creates a document.
    Tenant Beta attempts to UPDATE and DELETE Tenant Alpha's record.
    VERIFICATION: 0 rows modified, document remains intact.
    """
    doc_id = uuid.uuid4()

    # 1. Tenant Alpha creates the record
    async with get_tenant_db_session(str(tenant_alpha_id)) as session:
        doc = EnterpriseDocument(
            id=doc_id,
            tenant_id=tenant_alpha_id,
            title="Alpha Production Service Config",
            content="Critical infrastructure credentials and configs.",
            metadata_={"version": "1.0"}
        )
        session.add(doc)
        await session.commit()

    # 2. Tenant Beta attempts to overwrite Alpha's document
    async with get_tenant_db_session(str(tenant_beta_id)) as session:
        update_stmt = (
            update(EnterpriseDocument)
            .where(EnterpriseDocument.id == doc_id)
            .values(title="Hacked Title")
        )
        res = await session.execute(update_stmt)
        await session.commit()

        # The row is invisible to Beta, so 0 rows are affected
        assert res.rowcount == 0

    # 3. Tenant Beta attempts to DELETE Alpha's document
    async with get_tenant_db_session(str(tenant_beta_id)) as session:
        delete_stmt = delete(EnterpriseDocument).where(
            EnterpriseDocument.id == doc_id)
        res = await session.execute(delete_stmt)
        await session.commit()

        assert res.rowcount == 0

    # 4. Verify original record is unchanged
    async with get_tenant_db_session(str(tenant_alpha_id)) as session:
        doc_in_db = await session.get(EnterpriseDocument, doc_id)
        assert doc_in_db is not None
        assert doc_in_db.title == "Alpha Production Service Config"
