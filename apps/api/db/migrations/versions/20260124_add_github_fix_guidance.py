"""Add GitHub fix guidance fields to runs table

Revision ID: 20260124_001
Revises: 20241223_001
Create Date: 2026-01-24

This migration adds fields for tracking resume steps and fix issue numbers
to support the GitHub @claude fix guidance feature.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260124_001"
down_revision: str | None = "20241223_001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add last_resumed_step and fix_issue_number columns to runs table."""
    op.add_column(
        "runs",
        sa.Column("last_resumed_step", sa.String(64), nullable=True),
    )
    op.add_column(
        "runs",
        sa.Column("fix_issue_number", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Remove last_resumed_step and fix_issue_number columns from runs table."""
    op.drop_column("runs", "fix_issue_number")
    op.drop_column("runs", "last_resumed_step")
