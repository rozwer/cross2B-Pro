"""Add hearing_templates table

Revision ID: 20241223_001
Revises:
Create Date: 2024-12-23

This migration adds the hearing_templates table for storing reusable
workflow input configurations. Templates store ArticleHearingInput data
(without the confirmed field) that can be loaded and reused for new runs.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20241223_001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create hearing_templates table with indexes and triggers."""
    # Create table
    op.create_table(
        "hearing_templates",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_hearing_template_tenant_name"),
    )

    # Create indexes
    op.create_index("idx_hearing_templates_tenant_id", "hearing_templates", ["tenant_id"])
    op.create_index("idx_hearing_templates_name", "hearing_templates", ["name"])

    # Ensure update_updated_at_column function exists (PostgreSQL specific)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """
    )

    # Create trigger for updated_at (PostgreSQL specific)
    op.execute(
        """
        CREATE TRIGGER update_hearing_templates_updated_at
            BEFORE UPDATE ON hearing_templates
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
    )


def downgrade() -> None:
    """Drop hearing_templates table and related objects."""
    # Drop trigger first
    op.execute("DROP TRIGGER IF EXISTS update_hearing_templates_updated_at ON hearing_templates")

    # Drop indexes
    op.drop_index("idx_hearing_templates_name", table_name="hearing_templates")
    op.drop_index("idx_hearing_templates_tenant_id", table_name="hearing_templates")

    # Drop table
    op.drop_table("hearing_templates")
