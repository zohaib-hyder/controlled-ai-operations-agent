"""Tool execution metadata and per-actor admission windows."""

import sqlalchemy as sa
from alembic import op

revision = "0003_tool_execution"
down_revision = "0002_authentication"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tool_executions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.String(64), nullable=False),
        sa.Column("tool_version", sa.String(20), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("error_category", sa.String(40)),
        sa.ForeignKeyConstraint(
            ["tenant_id", "actor_id"], ["users.tenant_id", "users.id"]
        ),
        sa.CheckConstraint("duration_ms >= 0"),
        sa.CheckConstraint("outcome IN ('running', 'success', 'error', 'cancelled')"),
    )
    for column in ("tenant_id", "actor_id", "correlation_id"):
        op.create_index(f"ix_tool_executions_{column}", "tool_executions", [column])
    op.create_table(
        "tool_rate_buckets",
        sa.Column(
            "tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), primary_key=True
        ),
        sa.Column("actor_id", sa.Uuid(), primary_key=True),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "actor_id"], ["users.tenant_id", "users.id"]
        ),
    )


def downgrade():
    raise RuntimeError("Tool audit removal requires a reviewed retention/restore plan")
