"""Likhitha Day 4–5: evidence, investigations, audit, indexes, source columns, minhash.

Revision ID: l20260511_likhitha_day4_5
Revises: d06fdb8072f3
Create Date: 2026-05-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "l20260511_likhitha_day4_5"
down_revision = "d06fdb8072f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("raw_events", sa.Column("minhash_signature", sa.JSON(), nullable=True))

    op.add_column("sources", sa.Column("tier", sa.Integer(), server_default="2", nullable=True))
    op.add_column("sources", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("sources", sa.Column("reliability_multiplier", sa.Float(), server_default="1.0", nullable=True))
    op.add_column("sources", sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sources", sa.Column("events_today", sa.Integer(), server_default="0", nullable=True))
    op.add_column("sources", sa.Column("error_message", sa.String(), nullable=True))

    op.alter_column("evidence_packages", "alert_id", existing_type=UUID(), nullable=True)
    op.add_column("evidence_packages", sa.Column("entity_id", UUID(as_uuid=True), nullable=True))
    op.add_column("evidence_packages", sa.Column("analyst_id", UUID(as_uuid=True), nullable=True))
    op.add_column("evidence_packages", sa.Column("case_id", sa.String(), nullable=True))
    op.add_column("evidence_packages", sa.Column("included_entity_ids", sa.JSON(), nullable=True))
    op.add_column("evidence_packages", sa.Column("case_metadata", sa.JSON(), nullable=True))
    op.add_column("evidence_packages", sa.Column("file_path", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_evidence_packages_entity_id",
        "evidence_packages",
        "entities",
        ["entity_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_evidence_packages_analyst_id",
        "evidence_packages",
        "users",
        ["analyst_id"],
        ["id"],
    )

    op.create_table(
        "investigations",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("analyst_id", UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("entity_ids", sa.JSON(), nullable=True),
        sa.Column("evidence_package_id", UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["analyst_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["evidence_package_id"], ["evidence_packages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "alert_status_history",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("alert_id", UUID(as_uuid=True), nullable=False),
        sa.Column("old_status", sa.String(), nullable=True),
        sa.Column("new_status", sa.String(), nullable=False),
        sa.Column("analyst_id", UUID(as_uuid=True), nullable=True),
        sa.Column("analyst_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["alert_id"], ["risk_alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analyst_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_status_history_alert_id", "alert_status_history", ["alert_id"])

    op.create_index("idx_risk_alerts_created_at", "risk_alerts", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_risk_alerts_created_at", table_name="risk_alerts")
    op.drop_index("ix_alert_status_history_alert_id", table_name="alert_status_history")
    op.drop_table("alert_status_history")
    op.drop_table("investigations")

    op.drop_constraint("fk_evidence_packages_analyst_id", "evidence_packages", type_="foreignkey")
    op.drop_constraint("fk_evidence_packages_entity_id", "evidence_packages", type_="foreignkey")
    op.drop_column("evidence_packages", "file_path")
    op.drop_column("evidence_packages", "case_metadata")
    op.drop_column("evidence_packages", "included_entity_ids")
    op.drop_column("evidence_packages", "case_id")
    op.drop_column("evidence_packages", "analyst_id")
    op.drop_column("evidence_packages", "entity_id")
    op.alter_column("evidence_packages", "alert_id", existing_type=UUID(), nullable=False)

    op.drop_column("sources", "error_message")
    op.drop_column("sources", "events_today")
    op.drop_column("sources", "last_crawled_at")
    op.drop_column("sources", "reliability_multiplier")
    op.drop_column("sources", "description")
    op.drop_column("sources", "tier")

    op.drop_column("raw_events", "minhash_signature")
