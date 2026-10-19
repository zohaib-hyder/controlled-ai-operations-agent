"""Evaluation-only proposals and immutable decision receipts."""

import sqlalchemy as sa
from alembic import op

revision = "0006_policy_decisions"
down_revision = "0005_policy_applicability"
branch_labels = None
depends_on = None


def upgrade():
    for name, extra, constraints in (
        (
            "action_proposals",
            [
                sa.Column("actor_id", sa.Uuid(), nullable=False),
                sa.Column("investigation_id", sa.Uuid(), nullable=False),
            ],
            [
                sa.ForeignKeyConstraint(
                    ["tenant_id", "actor_id"], ["users.tenant_id", "users.id"]
                ),
                sa.ForeignKeyConstraint(
                    ["tenant_id", "investigation_id"],
                    ["investigations.tenant_id", "investigations.id"],
                ),
                sa.UniqueConstraint("tenant_id", "id"),
            ],
        ),
        (
            "policy_decision_receipts",
            [
                sa.Column("proposal_id", sa.Uuid(), nullable=False),
                sa.Column("sequence", sa.Integer(), nullable=False),
            ],
            [
                sa.ForeignKeyConstraint(
                    ["tenant_id", "proposal_id"],
                    ["action_proposals.tenant_id", "action_proposals.id"],
                ),
                sa.UniqueConstraint("tenant_id", "proposal_id", "sequence"),
            ],
        ),
    ):
        op.create_table(
            name,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("payload", sa.JSON(), nullable=False),
            *extra,
            *constraints,
        )
        for column in ("tenant_id", *(c.name for c in extra if c.name != "sequence")):
            op.create_index(f"ix_{name}_{column}", name, [column])


def downgrade():
    op.drop_table("policy_decision_receipts")
    op.drop_table("action_proposals")
