"""controlled_execution"""

import sqlalchemy as sa
from alembic import op

revision = "0007_controlled_execution"
down_revision = "0006_policy_decisions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "uq_receipt_tenant_id", "policy_decision_receipts", ["tenant_id", "id"]
    )
    op.create_table(
        "approval_requests",
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("decision_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("reviewer_session_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("binding", sa.JSON(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED','EXPIRED','CANCELLED','INVALIDATED')"
        ),
        sa.CheckConstraint("reviewer_id IS NULL OR reviewer_id <> requested_by"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "decision_id"],
            ["policy_decision_receipts.tenant_id", "policy_decision_receipts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "proposal_id"],
            ["action_proposals.tenant_id", "action_proposals.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "requested_by"],
            ["users.tenant_id", "users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "reviewer_id"],
            ["users.tenant_id", "users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "reviewer_session_id"],
            ["auth_sessions.tenant_id", "auth_sessions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id"),
        sa.UniqueConstraint("tenant_id", "proposal_id"),
    )
    op.create_index(
        op.f("ix_approval_requests_proposal_id"),
        "approval_requests",
        ["proposal_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_approval_requests_tenant_id"),
        "approval_requests",
        ["tenant_id"],
        unique=False,
    )
    op.create_table(
        "action_executions",
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("decision_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("approval_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "actor_id"],
            ["users.tenant_id", "users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "approval_id"],
            ["approval_requests.tenant_id", "approval_requests.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "decision_id"],
            ["policy_decision_receipts.tenant_id", "policy_decision_receipts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "proposal_id"],
            ["action_proposals.tenant_id", "action_proposals.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "approval_id"),
        sa.UniqueConstraint("tenant_id", "id"),
        sa.UniqueConstraint("tenant_id", "idempotency_key"),
        sa.UniqueConstraint("tenant_id", "proposal_id"),
    )
    op.create_index(
        op.f("ix_action_executions_proposal_id"),
        "action_executions",
        ["proposal_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_action_executions_tenant_id"),
        "action_executions",
        ["tenant_id"],
        unique=False,
    )
    op.create_table(
        "approval_decisions",
        sa.Column("approval_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=300), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "actor_id"],
            ["users.tenant_id", "users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "approval_id"],
            ["approval_requests.tenant_id", "approval_requests.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "approval_id", "sequence"),
    )
    op.create_index(
        op.f("ix_approval_decisions_approval_id"),
        "approval_decisions",
        ["approval_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_approval_decisions_tenant_id"),
        "approval_decisions",
        ["tenant_id"],
        unique=False,
    )
    op.create_table(
        "action_execution_events",
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "execution_id"],
            ["action_executions.tenant_id", "action_executions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "execution_id", "sequence"),
    )
    op.create_index(
        op.f("ix_action_execution_events_execution_id"),
        "action_execution_events",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_action_execution_events_tenant_id"),
        "action_execution_events",
        ["tenant_id"],
        unique=False,
    )
    op.create_table(
        "business_records",
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=True),
        sa.Column("ticket_id", sa.Uuid(), nullable=True),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("content", sa.String(length=500), nullable=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('customer_note','ticket_note','reactivation_request')"
        ),
        sa.CheckConstraint(
            "(CASE WHEN customer_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN ticket_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN account_id IS NOT NULL THEN 1 ELSE 0 END) = 1"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "account_id"],
            ["accounts.tenant_id", "accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "customer_id"],
            ["customers.tenant_id", "customers.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "execution_id"],
            ["action_executions.tenant_id", "action_executions.id"],
            initially="DEFERRED",
            deferrable=True,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "ticket_id"],
            ["tickets.tenant_id", "tickets.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "execution_id"),
    )
    op.create_index(
        op.f("ix_business_records_execution_id"),
        "business_records",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_business_records_tenant_id"),
        "business_records",
        ["tenant_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_business_records_tenant_id"), table_name="business_records")
    op.drop_index(
        op.f("ix_business_records_execution_id"), table_name="business_records"
    )
    op.drop_table("business_records")
    op.drop_index(
        op.f("ix_action_execution_events_tenant_id"),
        table_name="action_execution_events",
    )
    op.drop_index(
        op.f("ix_action_execution_events_execution_id"),
        table_name="action_execution_events",
    )
    op.drop_table("action_execution_events")
    op.drop_index(
        op.f("ix_approval_decisions_tenant_id"), table_name="approval_decisions"
    )
    op.drop_index(
        op.f("ix_approval_decisions_approval_id"), table_name="approval_decisions"
    )
    op.drop_table("approval_decisions")
    op.drop_index(
        op.f("ix_action_executions_tenant_id"), table_name="action_executions"
    )
    op.drop_index(
        op.f("ix_action_executions_proposal_id"), table_name="action_executions"
    )
    op.drop_table("action_executions")
    op.drop_index(
        op.f("ix_approval_requests_tenant_id"), table_name="approval_requests"
    )
    op.drop_index(
        op.f("ix_approval_requests_proposal_id"), table_name="approval_requests"
    )
    op.drop_table("approval_requests")

    op.drop_constraint(
        "uq_receipt_tenant_id", "policy_decision_receipts", type_="unique"
    )
