"""Add uppercase investigating and resolved alertstatus values.

Revision ID: 20260531_status_casefix
Revises: 20260531_escalated
Create Date: 2026-05-31 23:15:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260531_status_casefix"
down_revision = "20260531_escalated"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
DO $$
BEGIN
    ALTER TYPE alertstatus ADD VALUE IF NOT EXISTS 'INVESTIGATING';
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
"""
    )
    op.execute(
        """
DO $$
BEGIN
    ALTER TYPE alertstatus ADD VALUE IF NOT EXISTS 'RESOLVED';
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
"""
    )


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely in-place.
    pass