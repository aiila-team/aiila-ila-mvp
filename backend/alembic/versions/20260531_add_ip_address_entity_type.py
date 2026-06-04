"""Add ip_address to EntityType enum.

Revision ID: 20260531_ipaddr_enum
Revises: 
Create Date: 2026-05-31 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260531_ipaddr_enum"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
DO $$
DECLARE
    enum_type_name text;
BEGIN
    SELECT t.typname
    INTO enum_type_name
    FROM pg_type t
    JOIN pg_enum e ON e.enumtypid = t.oid
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname = current_schema()
    GROUP BY t.typname
    HAVING bool_or(e.enumlabel = 'person')
       AND bool_or(e.enumlabel = 'phone')
       AND bool_or(e.enumlabel = 'email')
       AND bool_or(e.enumlabel = 'upi_account')
       AND bool_or(e.enumlabel = 'social_handle')
       AND bool_or(e.enumlabel = 'telegram')
       AND bool_or(e.enumlabel = 'website')
       AND bool_or(e.enumlabel = 'imei')
       AND bool_or(e.enumlabel = 'crypto_wallet')
    LIMIT 1;

    IF enum_type_name IS NOT NULL THEN
        EXECUTE format(
            'ALTER TYPE %I ADD VALUE IF NOT EXISTS %L',
            enum_type_name,
            'ip_address'
        );
    END IF;
END $$;
"""
    )


def downgrade() -> None:
    # PostgreSQL does not support removing enum values cleanly.
    pass
