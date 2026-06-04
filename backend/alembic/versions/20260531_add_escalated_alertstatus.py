"""Add escalated to alertstatus enum.

Revision ID: 20260531_escalated
Revises: p1_api_20260531
Create Date: 2026-05-31 23:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260531_escalated"
down_revision = "p1_api_20260531"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
DO $$
BEGIN
    ALTER TYPE alertstatus ADD VALUE IF NOT EXISTS 'ESCALATED';
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
"""
    )


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely in-place.
    pass