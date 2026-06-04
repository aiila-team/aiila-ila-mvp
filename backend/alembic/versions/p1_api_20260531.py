"""Port modular API support tables and alert statuses.

Revision ID: p1_api_20260531
Revises: 0f22131e3d37
Create Date: 2026-05-31 22:15:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "p1_api_20260531"
down_revision = "0f22131e3d37"
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

    op.create_table(
        "alert_status_history",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("alert_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("old_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=False),
        sa.Column("analyst_id", sa.UUID(as_uuid=False), nullable=True),
        sa.Column("analyst_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["alert_id"], ["risk_alerts.id"]),
        sa.ForeignKeyConstraint(["analyst_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alert_status_history_alert_id"), "alert_status_history", ["alert_id"], unique=False)

    op.create_table(
        "investigations",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("analyst_id", sa.UUID(as_uuid=False), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("entity_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evidence_package_id", sa.UUID(as_uuid=False), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["analyst_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["evidence_package_id"], ["evidence_packages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("investigations")
    op.drop_index(op.f("ix_alert_status_history_alert_id"), table_name="alert_status_history")
    op.drop_table("alert_status_history")