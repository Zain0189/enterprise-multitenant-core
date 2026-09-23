"""create_initial_multitenant_schema_with_rls

Revision ID: cfbdc1dd6a96
Revises: 
Create Date: 2026-09-23 11:34:18.960613

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cfbdc1dd6a96'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------
    # 1. EXTENSIONS
    # -------------------------------------------------------------
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # -------------------------------------------------------------
    # 2. TENANTS TABLE
    # -------------------------------------------------------------
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("is_active", sa.Boolean(),
                  server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name", name="uq_tenants_name"),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    # -------------------------------------------------------------
    # 3. USERS TABLE (Tenant Scoped)
    # -------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=30),
                  server_default="viewer", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "email", name="uq_tenant_user_email"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    # -------------------------------------------------------------
    # 4. ENTERPRISE DOCUMENTS TABLE (Tenant Scoped)
    # -------------------------------------------------------------
    op.create_table(
        "enterprise_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()),
                  server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey(
            "users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documents_tenant_id",
                    "enterprise_documents", ["tenant_id"])

    # -------------------------------------------------------------
    # 5. PERMISSIONS FOR APPLICATION ROLE
    # -------------------------------------------------------------
    # Ensure app_user has full read/write access to schemas and tables
    op.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;")
    op.execute(
        "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;")

    # -------------------------------------------------------------
    # 6. POSTGRESQL ROW-LEVEL SECURITY (RLS) POLICIES
    # -------------------------------------------------------------
    # Enable RLS on the tenant-isolated tables
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE enterprise_documents ENABLE ROW LEVEL SECURITY;")

    # Policy for USERS table:
    # Restricts SELECT, INSERT, UPDATE, DELETE to rows matching the active session tenant.
    op.execute("""
        CREATE POLICY tenant_isolation_users ON users
        FOR ALL
        TO app_user
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
    """)

    # Policy for ENTERPRISE_DOCUMENTS table:
    op.execute("""
        CREATE POLICY tenant_isolation_documents ON enterprise_documents
        FOR ALL
        TO app_user
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
    """)


def downgrade() -> None:
    # 1. Drop Policies
    op.execute(
        "DROP POLICY IF EXISTS tenant_isolation_documents ON enterprise_documents;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_users ON users;")

    # 2. Disable RLS
    op.execute("ALTER TABLE enterprise_documents DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY;")

    # 3. Drop Tables (in reverse dependency order)
    op.drop_table("enterprise_documents")
    op.drop_table("users")
    op.drop_table("tenants")
