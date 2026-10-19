"""Add tenant-bound authentication without replacing existing business records."""

import sqlalchemy as sa
from alembic import op

revision = "0002_authentication"
down_revision = "5cdee4cd2488"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("users_role_check", "users", type_="check")
    op.execute("UPDATE users SET role = 'reviewer' WHERE role = 'approver'")
    # Only rename the original synthetic reviewer emails; preserve user IDs and other addresses.
    op.execute(
        "UPDATE users SET email = replace(email, 'approver.', 'reviewer.') WHERE email IN ('approver.0@example.com', 'approver.1@example.com') AND role = 'reviewer'"
    )
    op.create_check_constraint(
        "users_role_check",
        "users",
        "role IN ('operator', 'reviewer', 'admin', 'auditor')",
    )
    op.add_column("users", sa.Column("password_hash", sa.String(512), nullable=True))
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_index(
        "uq_users_normalized_email", "users", [sa.text("lower(email)")], unique=True
    )
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
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
        sa.UniqueConstraint("tenant_id", "id"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "user_id"], ["users.tenant_id", "users.id"]
        ),
        sa.CheckConstraint("expires_at > created_at"),
    )
    for column in ("tenant_id", "user_id", "expires_at"):
        op.create_index(f"ix_auth_sessions_{column}", "auth_sessions", [column])
    op.create_table(
        "login_buckets",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_login_buckets_window_started_at", "login_buckets", ["window_started_at"]
    )
    op.create_table(
        "security_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id")),
        sa.Column("actor_id", sa.Uuid()),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("resource_type", sa.String(40)),
        sa.Column("resource_id", sa.Uuid()),
        sa.Column("outcome", sa.String(24), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["tenant_id", "actor_id"], ["users.tenant_id", "users.id"]
        ),
    )
    for column in ("tenant_id", "event_type", "request_id"):
        op.create_index(f"ix_security_events_{column}", "security_events", [column])


def downgrade():
    raise RuntimeError(
        "Authentication downgrade would discard security records. Restore a reviewed backup instead."
    )
