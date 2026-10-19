from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    column,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Identity:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Tenant(Identity, Base):
    __tablename__ = "tenants"
    name: Mapped[str] = mapped_column(String(120), unique=True)


class Scoped(Identity):
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), index=True, nullable=False
    )


class User(Scoped, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "email"),
        Index("uq_users_normalized_email", func.lower(column("email")), unique=True),
        CheckConstraint(
            "role IN ('operator', 'reviewer', 'admin', 'auditor')",
            name="users_role_check",
        ),
    )
    email: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(24))
    password_hash: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default="true", default=True
    )


class Customer(Scoped, Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "email"),
    )
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200))
    accounts: Mapped[list["Account"]] = relationship(back_populates="customer")


class Account(Scoped, Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "customer_id"], ["customers.tenant_id", "customers.id"]
        ),
        CheckConstraint("status IN ('active', 'blocked', 'inactive')"),
        CheckConstraint("evidence_version > 0"),
    )
    customer_id: Mapped[UUID] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(String(24))
    block_reason: Mapped[str | None] = mapped_column(String(120))
    evidence_version: Mapped[int] = mapped_column(Integer, default=1)
    customer: Mapped[Customer] = relationship(back_populates="accounts")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="account")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")


class Ticket(Scoped, Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "account_id"], ["accounts.tenant_id", "accounts.id"]
        ),
        ForeignKeyConstraint(
            ["tenant_id", "duplicate_of_id"], ["tickets.tenant_id", "tickets.id"]
        ),
        CheckConstraint("status IN ('open', 'closed')"),
    )
    account_id: Mapped[UUID] = mapped_column(index=True)
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(24))
    duplicate_of_id: Mapped[UUID | None] = mapped_column(index=True)
    account: Mapped[Account] = relationship(back_populates="tickets")


class Transaction(Scoped, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "account_id"], ["accounts.tenant_id", "accounts.id"]
        ),
        CheckConstraint("amount_minor >= 0"),
        CheckConstraint("status IN ('paid', 'unpaid', 'disputed')"),
    )
    account_id: Mapped[UUID] = mapped_column(index=True)
    reference: Mapped[str] = mapped_column(String(80), unique=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(24))
    account: Mapped[Account] = relationship(back_populates="transactions")


class Policy(Scoped, Base):
    __tablename__ = "policies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "key", "version"),
        CheckConstraint("version > 0"),
    )
    key: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(1000))
    rules: Mapped[dict] = mapped_column(JSON)
    category: Mapped[str] = mapped_column(
        String(40), default="operations", server_default="operations"
    )
    resource_type: Mapped[str] = mapped_column(
        String(40), default="account", server_default="account"
    )
    effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("'2026-01-01T00:00:00Z'")
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    account_states: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'")
    )
    scenarios: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'")
    )


class AuthSession(Scoped, Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        ForeignKeyConstraint(["tenant_id", "user_id"], ["users.tenant_id", "users.id"]),
        CheckConstraint("expires_at > created_at"),
    )
    user_id: Mapped[UUID] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LoginBucket(Base):
    """Global abuse-protection metadata: opaque digests, no raw identity/IP."""

    __tablename__ = "login_buckets"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )


class SecurityEvent(Identity, Base):
    __tablename__ = "security_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "actor_id"], ["users.tenant_id", "users.id"]
        ),
    )
    tenant_id: Mapped[UUID | None] = mapped_column(ForeignKey("tenants.id"), index=True)
    actor_id: Mapped[UUID | None]
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(40))
    resource_id: Mapped[UUID | None]
    outcome: Mapped[str] = mapped_column(String(24))
    request_id: Mapped[UUID] = mapped_column(index=True)


class ToolExecution(Base):
    __tablename__ = "tool_executions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "actor_id"], ["users.tenant_id", "users.id"]
        ),
        CheckConstraint("duration_ms >= 0"),
        CheckConstraint("outcome IN ('running', 'success', 'error', 'cancelled')"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    actor_id: Mapped[UUID] = mapped_column(index=True)
    tool_name: Mapped[str] = mapped_column(String(64))
    tool_version: Mapped[str] = mapped_column(String(20))
    outcome: Mapped[str] = mapped_column(String(16))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[float] = mapped_column(Float)
    correlation_id: Mapped[UUID] = mapped_column(index=True)
    error_category: Mapped[str | None] = mapped_column(String(40))


class ToolRateBucket(Base):
    __tablename__ = "tool_rate_buckets"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "actor_id"], ["users.tenant_id", "users.id"]
        ),
    )
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), primary_key=True)
    actor_id: Mapped[UUID] = mapped_column(primary_key=True)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer)


class Investigation(Scoped, Base):
    __tablename__ = "investigations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "actor_id", "idempotency_key"),
        ForeignKeyConstraint(
            ["tenant_id", "actor_id"], ["users.tenant_id", "users.id"]
        ),
        ForeignKeyConstraint(
            ["tenant_id", "customer_id"], ["customers.tenant_id", "customers.id"]
        ),
        ForeignKeyConstraint(
            ["tenant_id", "ticket_id"], ["tickets.tenant_id", "tickets.id"]
        ),
        CheckConstraint(
            "status IN ('CREATED','PLANNING','RUNNING','COMPLETED','NEEDS_REVIEW','FAILED','CANCELLED','BUDGET_EXCEEDED')"
        ),
        CheckConstraint(
            "version >= 1 AND event_sequence >= 1 AND checkpoint_sequence >= 1 AND current_step >= 0"
        ),
        Index(
            "ix_investigations_owner_history",
            "tenant_id",
            "actor_id",
            "created_at",
            "id",
        ),
    )
    actor_id: Mapped[UUID]
    customer_id: Mapped[UUID] = mapped_column(index=True)
    ticket_id: Mapped[UUID | None]
    goal: Mapped[str] = mapped_column(String(1000))
    context: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24), index=True)
    planner_type: Mapped[str] = mapped_column(String(40))
    planner_version: Mapped[str] = mapped_column(String(20))
    idempotency_key: Mapped[str] = mapped_column(String(80))
    request_hash: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer)
    event_sequence: Mapped[int] = mapped_column(Integer)
    checkpoint_sequence: Mapped[int] = mapped_column(Integer)
    current_step: Mapped[int] = mapped_column(Integer)
    budget_counters: Mapped[dict] = mapped_column(JSON)
    budget_limits: Mapped[dict] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[UUID | None]
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    stop_reason: Mapped[str | None] = mapped_column(String(80))
    final_result: Mapped[dict | None] = mapped_column(JSON)


class InvestigationStep(Scoped, Base):
    __tablename__ = "investigation_steps"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "investigation_id"],
            ["investigations.tenant_id", "investigations.id"],
        ),
        UniqueConstraint("tenant_id", "investigation_id", "step_id"),
        UniqueConstraint("tenant_id", "investigation_id", "step_index"),
        CheckConstraint("step_index > 0"),
    )
    investigation_id: Mapped[UUID] = mapped_column(index=True)
    step_id: Mapped[str] = mapped_column(String(40))
    step_index: Mapped[int] = mapped_column(Integer)
    definition: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16))


class InvestigationCheckpoint(Scoped, Base):
    __tablename__ = "investigation_checkpoints"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "investigation_id"],
            ["investigations.tenant_id", "investigations.id"],
        ),
        UniqueConstraint("tenant_id", "investigation_id", "sequence"),
        UniqueConstraint("tenant_id", "investigation_id", "applied_version"),
        CheckConstraint("sequence > 0 AND applied_version > 0 AND schema_version = 1"),
    )
    investigation_id: Mapped[UUID] = mapped_column(index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    applied_version: Mapped[int] = mapped_column(Integer)
    schema_version: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))


class InvestigationEvent(Scoped, Base):
    __tablename__ = "investigation_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "investigation_id"],
            ["investigations.tenant_id", "investigations.id"],
        ),
        UniqueConstraint("tenant_id", "investigation_id", "sequence"),
        CheckConstraint("sequence > 0"),
    )
    investigation_id: Mapped[UUID] = mapped_column(index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(60))
    data: Mapped[dict] = mapped_column(JSON)


class InvestigationEvidence(Scoped, Base):
    __tablename__ = "investigation_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "investigation_id"],
            ["investigations.tenant_id", "investigations.id"],
        ),
        ForeignKeyConstraint(
            ["tenant_id", "tool_execution_id"],
            ["tool_executions.tenant_id", "tool_executions.id"],
        ),
        UniqueConstraint("tenant_id", "investigation_id", "tool_execution_id"),
        UniqueConstraint("tenant_id", "investigation_id", "sequence"),
    )
    investigation_id: Mapped[UUID] = mapped_column(index=True)
    tool_execution_id: Mapped[UUID]
    sequence: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)


class ActionProposal(Scoped, Base):
    __tablename__ = "action_proposals"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        ForeignKeyConstraint(
            ["tenant_id", "actor_id"], ["users.tenant_id", "users.id"]
        ),
        ForeignKeyConstraint(
            ["tenant_id", "investigation_id"],
            ["investigations.tenant_id", "investigations.id"],
        ),
    )
    actor_id: Mapped[UUID] = mapped_column(index=True)
    investigation_id: Mapped[UUID] = mapped_column(index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class PolicyDecisionReceipt(Scoped, Base):
    __tablename__ = "policy_decision_receipts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_receipt_tenant_id"),
        ForeignKeyConstraint(
            ["tenant_id", "proposal_id"],
            ["action_proposals.tenant_id", "action_proposals.id"],
        ),
        UniqueConstraint("tenant_id", "proposal_id", "sequence"),
    )
    proposal_id: Mapped[UUID] = mapped_column(index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)


class ApprovalRequest(Scoped, Base):
    __tablename__ = "approval_requests"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "proposal_id"),
        ForeignKeyConstraint(
            ["tenant_id", "proposal_id"],
            ["action_proposals.tenant_id", "action_proposals.id"],
        ),
        ForeignKeyConstraint(
            ["tenant_id", "decision_id"],
            ["policy_decision_receipts.tenant_id", "policy_decision_receipts.id"],
        ),
        ForeignKeyConstraint(
            ["tenant_id", "requested_by"], ["users.tenant_id", "users.id"]
        ),
        ForeignKeyConstraint(
            ["tenant_id", "reviewer_id"], ["users.tenant_id", "users.id"]
        ),
        ForeignKeyConstraint(
            ["tenant_id", "reviewer_session_id"],
            ["auth_sessions.tenant_id", "auth_sessions.id"],
        ),
        CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED','EXPIRED','CANCELLED','INVALIDATED')"
        ),
        CheckConstraint("reviewer_id IS NULL OR reviewer_id <> requested_by"),
    )
    proposal_id: Mapped[UUID] = mapped_column(index=True)
    decision_id: Mapped[UUID]
    requested_by: Mapped[UUID]
    reviewer_id: Mapped[UUID | None]
    reviewer_session_id: Mapped[UUID | None]
    status: Mapped[str] = mapped_column(String(24))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    binding: Mapped[dict] = mapped_column(JSON)


class ApprovalDecision(Scoped, Base):
    __tablename__ = "approval_decisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "approval_id"],
            ["approval_requests.tenant_id", "approval_requests.id"],
        ),
        ForeignKeyConstraint(
            ["tenant_id", "actor_id"], ["users.tenant_id", "users.id"]
        ),
        UniqueConstraint("tenant_id", "approval_id", "sequence"),
    )
    approval_id: Mapped[UUID] = mapped_column(index=True)
    actor_id: Mapped[UUID]
    sequence: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str] = mapped_column(String(300))


class ActionExecution(Scoped, Base):
    __tablename__ = "action_executions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "proposal_id"),
        UniqueConstraint("tenant_id", "idempotency_key"),
        UniqueConstraint("tenant_id", "approval_id"),
        ForeignKeyConstraint(
            ["tenant_id", "proposal_id"],
            ["action_proposals.tenant_id", "action_proposals.id"],
        ),
        ForeignKeyConstraint(
            ["tenant_id", "decision_id"],
            ["policy_decision_receipts.tenant_id", "policy_decision_receipts.id"],
        ),
        ForeignKeyConstraint(
            ["tenant_id", "actor_id"], ["users.tenant_id", "users.id"]
        ),
        ForeignKeyConstraint(
            ["tenant_id", "approval_id"],
            ["approval_requests.tenant_id", "approval_requests.id"],
        ),
    )
    proposal_id: Mapped[UUID] = mapped_column(index=True)
    decision_id: Mapped[UUID]
    actor_id: Mapped[UUID]
    approval_id: Mapped[UUID | None]
    idempotency_key: Mapped[str] = mapped_column(String(80))
    request_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)


class ActionExecutionEvent(Scoped, Base):
    __tablename__ = "action_execution_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "execution_id"],
            ["action_executions.tenant_id", "action_executions.id"],
        ),
        UniqueConstraint("tenant_id", "execution_id", "sequence"),
    )
    execution_id: Mapped[UUID] = mapped_column(index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(60))
    correlation_id: Mapped[UUID]


class BusinessRecord(Scoped, Base):
    __tablename__ = "business_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "execution_id"),
        ForeignKeyConstraint(
            ["tenant_id", "execution_id"],
            ["action_executions.tenant_id", "action_executions.id"],
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "customer_id"], ["customers.tenant_id", "customers.id"]
        ),
        ForeignKeyConstraint(
            ["tenant_id", "ticket_id"], ["tickets.tenant_id", "tickets.id"]
        ),
        ForeignKeyConstraint(
            ["tenant_id", "account_id"], ["accounts.tenant_id", "accounts.id"]
        ),
        CheckConstraint(
            "(CASE WHEN customer_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN ticket_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN account_id IS NOT NULL THEN 1 ELSE 0 END) = 1"
        ),
        CheckConstraint(
            "kind IN ('customer_note','ticket_note','reactivation_request')"
        ),
    )
    execution_id: Mapped[UUID] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column(String(40))
    customer_id: Mapped[UUID | None]
    ticket_id: Mapped[UUID | None]
    account_id: Mapped[UUID | None]
    content: Mapped[str | None] = mapped_column(String(500))


class ExecutionJob(Scoped, Base):
    __tablename__ = "execution_jobs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "proposal_id"),
        UniqueConstraint("tenant_id", "idempotency_key"),
        ForeignKeyConstraint(
            ["tenant_id", "proposal_id"],
            ["action_proposals.tenant_id", "action_proposals.id"],
        ),
        ForeignKeyConstraint(
            ["tenant_id", "actor_id"], ["users.tenant_id", "users.id"]
        ),
        ForeignKeyConstraint(
            ["tenant_id", "session_id"], ["auth_sessions.tenant_id", "auth_sessions.id"]
        ),
        ForeignKeyConstraint(
            ["tenant_id", "receipt_id"],
            ["action_executions.tenant_id", "action_executions.id"],
        ),
        CheckConstraint(
            "status IN ('QUEUED','CLAIMED','RUNNING','RETRY_SCHEDULED','RECONCILIATION_REQUIRED','COMPLETED','FAILED','DEAD_LETTERED','CANCELLED')"
        ),
        CheckConstraint(
            "attempt_count >= 0 AND max_attempts BETWEEN 1 AND 5 AND priority BETWEEN 0 AND 10 AND fence >= 0"
        ),
        Index("ix_jobs_eligible", "status", "next_run_at", "tenant_id"),
    )
    proposal_id: Mapped[UUID] = mapped_column()
    actor_id: Mapped[UUID] = mapped_column()
    session_id: Mapped[UUID] = mapped_column()
    action_name: Mapped[str] = mapped_column(String(80))
    action_version: Mapped[str] = mapped_column(String(20))
    idempotency_key: Mapped[str] = mapped_column(String(80))
    binding_hash: Mapped[str] = mapped_column(String(64))
    command: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="QUEUED")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    retry_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[str | None] = mapped_column(String(64))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fence: Mapped[int] = mapped_column(Integer, default=0)
    receipt_id: Mapped[UUID | None] = mapped_column()
    last_error: Mapped[str | None] = mapped_column(String(80))


class ExecutionJobAttempt(Scoped, Base):
    __tablename__ = "execution_job_attempts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "job_id"], ["execution_jobs.tenant_id", "execution_jobs.id"]
        ),
        UniqueConstraint("tenant_id", "job_id", "number"),
    )
    job_id: Mapped[UUID] = mapped_column()
    number: Mapped[int] = mapped_column(Integer)
    fence: Mapped[int] = mapped_column(Integer)
    correlation_id: Mapped[UUID] = mapped_column()
    outcome: Mapped[str] = mapped_column(String(40))
    error_category: Mapped[str | None] = mapped_column(String(80))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExecutionJobEvent(Scoped, Base):
    __tablename__ = "execution_job_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "job_id"], ["execution_jobs.tenant_id", "execution_jobs.id"]
        ),
    )
    job_id: Mapped[UUID] = mapped_column()
    state: Mapped[str] = mapped_column(String(32))
    category: Mapped[str] = mapped_column(String(80))
    correlation_id: Mapped[UUID] = mapped_column()


class ExecutionDeadLetter(Scoped, Base):
    __tablename__ = "execution_dead_letters"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "job_id"], ["execution_jobs.tenant_id", "execution_jobs.id"]
        ),
        UniqueConstraint("tenant_id", "job_id", "attempt_count"),
    )
    job_id: Mapped[UUID] = mapped_column()
    attempt_count: Mapped[int] = mapped_column(Integer)
    error_category: Mapped[str] = mapped_column(String(80))
    correlation_id: Mapped[UUID] = mapped_column()


class OperationsIncident(Scoped, Base):
    __tablename__ = "operations_incidents"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "condition_key"),
        ForeignKeyConstraint(
            ["tenant_id", "visible_actor_id"], ["users.tenant_id", "users.id"]
        ),
        ForeignKeyConstraint(
            ["tenant_id", "assigned_to"], ["users.tenant_id", "users.id"]
        ),
        ForeignKeyConstraint(
            ["tenant_id", "job_id"], ["execution_jobs.tenant_id", "execution_jobs.id"]
        ),
        ForeignKeyConstraint(
            ["tenant_id", "approval_id"],
            ["approval_requests.tenant_id", "approval_requests.id"],
        ),
        CheckConstraint(
            "status IN ('OPEN','ACKNOWLEDGED','INVESTIGATING','RESOLVED','CLOSED')"
        ),
        CheckConstraint("severity IN ('warning','critical')"),
        Index("ix_incidents_window", "tenant_id", "created_at", "id"),
        Index("ix_incidents_backlog", "tenant_id", "status", "severity"),
        Index("ix_incidents_source_job", "tenant_id", "category", "job_id"),
        Index("ix_incidents_source_approval", "tenant_id", "category", "approval_id"),
    )
    condition_key: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(String(24), default="OPEN")
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(240))
    visible_actor_id: Mapped[UUID] = mapped_column()
    job_id: Mapped[UUID | None]
    approval_id: Mapped[UUID | None]
    source_event_id: Mapped[UUID | None]
    assigned_to: Mapped[UUID | None]
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_note: Mapped[str | None] = mapped_column(String(300))


class OperationsIncidentEvent(Scoped, Base):
    __tablename__ = "operations_incident_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "incident_id"],
            ["operations_incidents.tenant_id", "operations_incidents.id"],
        ),
        ForeignKeyConstraint(
            ["tenant_id", "actor_id"], ["users.tenant_id", "users.id"]
        ),
        Index("ix_incident_events_window", "tenant_id", "created_at", "id"),
        Index("ix_incident_history", "tenant_id", "incident_id", "created_at", "id"),
    )
    incident_id: Mapped[UUID] = mapped_column()
    actor_id: Mapped[UUID | None]
    correlation_id: Mapped[UUID] = mapped_column()
    event_type: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(24))
    note: Mapped[str | None] = mapped_column(String(300))


class OperationsConfig(Scoped, Base):
    __tablename__ = "operations_config"
    __table_args__ = (UniqueConstraint("tenant_id"),)
    thresholds: Mapped[dict] = mapped_column(JSON)


class OperationsRateBucket(Scoped, Base):
    __tablename__ = "operations_rate_buckets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "actor_id", "kind"),
        ForeignKeyConstraint(
            ["tenant_id", "actor_id"], ["users.tenant_id", "users.id"]
        ),
    )
    actor_id: Mapped[UUID] = mapped_column()
    kind: Mapped[str] = mapped_column(String(12))
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer)


class WorkerObservation(Base):
    """Private infrastructure liveness, not tenant/customer data; never returned raw."""

    __tablename__ = "worker_observations"
    owner: Mapped[str] = mapped_column(String(64), primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    stopped: Mapped[bool] = mapped_column(Boolean)


# Bounded command-center aggregations and stable timelines.
for _table in (
    Investigation.__table__,
    ActionProposal.__table__,
    PolicyDecisionReceipt.__table__,
    ApprovalRequest.__table__,
    ApprovalDecision.__table__,
    ActionExecution.__table__,
    ActionExecutionEvent.__table__,
    ExecutionJob.__table__,
    ExecutionJobEvent.__table__,
    SecurityEvent.__table__,
    InvestigationEvent.__table__,
    InvestigationEvidence.__table__,
):
    Index(
        "ix_ops_" + _table.name + "_window",
        _table.c.tenant_id,
        _table.c.created_at,
        _table.c.id,
    )
Index(
    "ix_ops_tools_window",
    ToolExecution.tenant_id,
    ToolExecution.started_at,
    ToolExecution.id,
)
Index(
    "ix_ops_approvals_backlog",
    ApprovalRequest.tenant_id,
    ApprovalRequest.status,
    ApprovalRequest.expires_at,
)
Index(
    "ix_ops_jobs_backlog",
    ExecutionJob.tenant_id,
    ExecutionJob.status,
    ExecutionJob.created_at,
)
