from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.tools.contracts import Contract

Status = Literal["OPEN", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED", "CLOSED"]
TRANSITIONS = {
    "OPEN": {"ACKNOWLEDGED"},
    "ACKNOWLEDGED": {"INVESTIGATING", "RESOLVED"},
    "INVESTIGATING": {"RESOLVED"},
    "RESOLVED": {"CLOSED"},
}


class Window(Contract):
    range: Literal["24h", "7d", "30d", "custom"] = "24h"
    start: datetime | None = None
    end: datetime | None = None

    @field_validator("start", "end", mode="before")
    @classmethod
    def dates(cls, v):
        if isinstance(v, str):
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if v is not None:
            if v.tzinfo is None:
                raise ValueError("Explicit UTC offset required")
            return v.astimezone(UTC)
        return v

    @model_validator(mode="after")
    def bounds(self):
        if self.range == "custom":
            if (
                not self.start
                or not self.end
                or not timedelta(0) < self.end - self.start <= timedelta(days=31)
            ):
                raise ValueError("Custom range must be positive and at most 31 days")
        elif self.start or self.end:
            raise ValueError("Dates require custom range")
        return self

    def resolve(self, now):
        if self.range == "custom":
            return self.start, self.end
        return now - timedelta(days={"24h": 1, "7d": 7, "30d": 30}[self.range]), now


class Thresholds(Contract):
    dead_letter_backlog: int = Field(default=1, ge=1, le=1000)
    reconciliation_backlog: int = Field(default=1, ge=1, le=1000)
    queue_age_seconds: int = Field(default=300, ge=1, le=86400)
    worker_stale_seconds: int = Field(default=45, ge=5, le=300)
    failure_percent: int = Field(default=50, ge=1, le=100)
    failure_min_samples: int = Field(default=5, ge=1, le=1000)


class IncidentCommand(Contract):
    note: str = Field(min_length=5, max_length=300)
    assigned_to: UUID | None = None

    @field_validator("assigned_to", mode="before")
    @classmethod
    def parse_id(cls, v):
        return UUID(v) if isinstance(v, str) else v

    @field_validator("note")
    @classmethod
    def safe_note(cls, v):
        import re

        if re.search(
            r"(password|secret|token|api[_ -]?key)\s*[:=]|-----BEGIN", v, re.I
        ):
            raise ValueError("Do not submit credentials")
        if len(v.strip()) < 5:
            raise ValueError("A meaningful operator note is required")
        return v.strip()


class Rate(Contract):
    numerator: int
    denominator: int
    percent: float | None


class Summary(Contract):
    count: int
    mean_seconds: float | None
    p50_seconds: float | None
    p95_seconds: float | None


class Bucket(Contract):
    day: str
    investigations: int
    retries: int


class MetricData(Contract):
    investigation_counts: dict[str, int]
    job_counts: dict[str, int]
    investigation_completion: Rate
    job_success: Rate
    retry_rate: Rate
    dead_letter_rate: Rate
    approval_rejection: Rate
    investigation_duration: Summary
    approval_turnaround: Summary
    execution_latency: Summary
    volume: tuple[Bucket, ...] = Field(max_length=32)
    pending_approvals: int
    expiring_approvals: int
    open_incidents: int
    queue_depth: int
    oldest_queue_age_seconds: float | None
    reconciliation_backlog: int
    dead_letter_backlog: int
    lease_expirations: int


class Health(Contract):
    api: Literal["healthy", "degraded", "unavailable", "unknown"]
    database: Literal["healthy", "degraded", "unavailable", "unknown"]
    worker: Literal["healthy", "degraded", "unavailable", "unknown"]
    queue: Literal["healthy", "degraded", "unavailable", "unknown"]
    migration: Literal["healthy", "degraded", "unavailable", "unknown"]
    overall: Literal["healthy", "degraded", "unavailable", "unknown"]
    observed_at: datetime


class Alert(Contract):
    code: str
    severity: Literal["warning", "critical"]
    message: str


class Overview(Contract):
    start: datetime
    end: datetime
    snapshot_at: datetime
    scope: Literal["own", "tenant"]
    metrics: MetricData
    health: Health
    alerts: tuple[Alert, ...]
    thresholds: Thresholds
    recent: tuple["Activity", ...] = Field(max_length=50)


class Activity(Contract):
    id: UUID
    timestamp: datetime
    event_type: str
    source: str
    entity_id: UUID
    actor_id: UUID | None
    service: str
    correlation_id: UUID | None
    summary: str


class ActivityPage(Contract):
    items: tuple[Activity, ...] = Field(max_length=50)
    limit: int
    offset: int


class Link(Contract):
    kind: str
    id: UUID
    href: str


class Correlation(Contract):
    links: tuple[Link, ...] = Field(max_length=650)
    timeline: tuple[Activity, ...] = Field(max_length=50)
    truncated: bool


class IncidentView(Contract):
    id: UUID
    category: str
    severity: Literal["warning", "critical"]
    status: Status
    title: str
    description: str
    visible_actor_id: UUID
    job_id: UUID | None
    approval_id: UUID | None
    source_event_id: UUID | None
    assigned_to: UUID | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    resolution_note: str | None
    can_respond: bool


class IncidentEventView(Contract):
    id: UUID
    actor_id: UUID | None
    correlation_id: UUID
    event_type: str
    status: Status
    note: str | None
    created_at: datetime


class IncidentDetail(Contract):
    incident: IncidentView
    events: tuple[IncidentEventView, ...] = Field(max_length=100)


class IncidentPage(Contract):
    items: tuple[IncidentView, ...] = Field(max_length=50)
    limit: int
    offset: int


class Detection(Contract):
    created: int
