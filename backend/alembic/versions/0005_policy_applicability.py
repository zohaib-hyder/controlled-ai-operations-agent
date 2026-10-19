"""Effective policy windows and applicability metadata."""

import sqlalchemy as sa
from alembic import op

revision = "0005_policy_applicability"
down_revision = "0004_persistent_investigations"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "policies",
        sa.Column(
            "category", sa.String(40), nullable=False, server_default="operations"
        ),
    )
    op.add_column(
        "policies",
        sa.Column(
            "resource_type", sa.String(40), nullable=False, server_default="account"
        ),
    )
    op.add_column(
        "policies",
        sa.Column(
            "effective_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("'2026-01-01T00:00:00Z'"),
        ),
    )
    op.add_column("policies", sa.Column("expires_at", sa.DateTime(timezone=True)))
    for name in ("account_states", "scenarios"):
        op.add_column(
            "policies",
            sa.Column(name, sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        )
    # Deterministic synthetic baseline metadata, no customer state changes.
    op.execute(
        "UPDATE policies SET category = key, scenarios = json_build_array(key), account_states = CASE WHEN key = 'duplicate_ticket' THEN '[]'::json ELSE '[\"blocked\"]'::json END"
    )
    op.execute(
        "UPDATE policies SET expires_at = effective_at WHERE key = 'reactivation' AND version = 1"
    )


def downgrade():
    for name in (
        "scenarios",
        "account_states",
        "expires_at",
        "effective_at",
        "resource_type",
        "category",
    ):
        op.drop_column("policies", name)
