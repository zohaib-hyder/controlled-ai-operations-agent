import asyncio
import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from threading import BoundedSemaphore, Event, Lock
from time import monotonic
from uuid import UUID, uuid4

from pydantic import BaseModel, ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.permissions import Identity, Permission
from app.db.session import get_engine
from app.models.entities import ToolExecution, ToolRateBucket
from app.tools.context import ReadScope, ToolExecutionContext
from app.tools.contracts import Invocation, Result, SafeError
from app.tools.errors import MESSAGES, ToolError
from app.tools.handlers import build_registry
from app.tools.registry import ToolRegistry

logger = logging.getLogger("northstar.tools")


@dataclass
class RunState:
    invocation: Invocation
    correlation_id: UUID
    execution_id: UUID = field(default_factory=uuid4)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    clock: float = field(default_factory=monotonic)
    stop: Event = field(default_factory=Event)
    lock: Lock = field(default_factory=Lock)
    reason: str | None = None
    finished: bool = False
    required_permission: Permission | None = None

    def interrupt(self, code: str) -> None:
        with self.lock:
            if not self.finished:
                self.reason = self.reason or code
                self.stop.set()

    def result(self, code: str | None, data=None) -> Result:
        return Result(
            execution_id=self.execution_id,
            tool_name=self.invocation.tool_name,
            tool_version=self.invocation.tool_version,
            status="success"
            if code is None
            else "cancelled"
            if code == "cancelled"
            else "error",
            data=data if code is None else None,
            error=SafeError(code=code, message=MESSAGES[code]) if code else None,
            started_at=self.started_at,
            completed_at=datetime.now(UTC),
            duration_ms=float(round((monotonic() - self.clock) * 1000, 3)),
            correlation_id=self.correlation_id,
        )


class ToolExecutor:
    """Trusted in-process service. Handlers are static Python, not a sandbox."""

    def __init__(
        self,
        session_factory=None,
        registry: ToolRegistry | None = None,
        *,
        workers: int = 4,
        max_attempts: int = 30,
    ):
        if not 1 <= workers <= 8 or not 1 <= max_attempts <= 100:
            raise ValueError("Invalid executor bounds")
        self.session_factory = session_factory or sessionmaker(bind=get_engine())
        self.registry = registry or build_registry()
        self.pool = ThreadPoolExecutor(
            max_workers=workers, thread_name_prefix="northstar-tool"
        )
        self.slots = BoundedSemaphore(workers)
        self.max_attempts = max_attempts

    async def execute(
        self,
        invocation: Invocation,
        *,
        identity: Identity,
        correlation_id: UUID,
        required_permission: Permission | None = None,
    ) -> Result:
        state = RunState(
            invocation, correlation_id, required_permission=required_permission
        )
        # Copy/freeze validated input before dispatch: mutable caller dictionaries are not shared.
        invocation = Invocation.model_validate_json(invocation.model_dump_json())
        state.invocation = invocation
        if not self.slots.acquire(blocking=False):
            return state.result("capacity_exceeded")
        try:
            future = self.pool.submit(self._run, state, identity)
        except Exception:
            self.slots.release()
            return state.result("capacity_exceeded")
        future.add_done_callback(lambda completed: self.slots.release())
        wrapped = asyncio.wrap_future(future)
        try:
            timeout = self.registry.resolve(
                invocation.tool_name, invocation.tool_version
            ).timeout_seconds
        except ToolError:
            timeout = 2.0
        try:
            return await asyncio.wait_for(asyncio.shield(wrapped), timeout=timeout)
        except TimeoutError:
            state.interrupt("timeout")
            # Drain the bounded read worker and its audit before returning. Python cannot kill threads.
            return await asyncio.shield(wrapped)
        except asyncio.CancelledError:
            state.interrupt("cancelled")
            # Keep the slot until rollback/close/audit complete, even if the caller disappears.
            try:
                await asyncio.shield(wrapped)
            finally:
                raise

    def _context(
        self, session: Session, identity: Identity, state: RunState
    ) -> ToolExecutionContext:
        from fastapi import HTTPException

        from app.services.authentication import revalidate_identity

        try:
            trusted = revalidate_identity(session, identity)
        except HTTPException:
            raise ToolError("authentication_required") from None
        return ToolExecutionContext(
            trusted.user_id,
            trusted.tenant_id,
            trusted.role,
            trusted.permissions,
            trusted.session_id,
            state.correlation_id,
            state.execution_id,
            state.started_at,
        )

    def _begin_audit(self, context: ToolExecutionContext, state: RunState) -> bool:
        with self.session_factory() as session, session.begin():
            key = hashlib.sha256(
                f"{context.tenant_id}:{context.user_id}".encode()
            ).hexdigest()
            session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": int(key[:15], 16)}
            )
            bucket = session.get(ToolRateBucket, (context.tenant_id, context.user_id))
            if bucket is None:
                bucket = ToolRateBucket(
                    tenant_id=context.tenant_id,
                    actor_id=context.user_id,
                    window_started_at=datetime.now(UTC),
                    attempts=0,
                )
                session.add(bucket)
            elif bucket.window_started_at < datetime.now(UTC) - timedelta(seconds=60):
                bucket.window_started_at = datetime.now(UTC)
                bucket.attempts = 0
            limited = bucket.attempts >= self.max_attempts
            if not limited:
                bucket.attempts += 1
            session.add(
                ToolExecution(
                    id=state.execution_id,
                    tenant_id=context.tenant_id,
                    actor_id=context.user_id,
                    tool_name=state.invocation.tool_name,
                    tool_version=state.invocation.tool_version,
                    outcome="running",
                    started_at=state.started_at,
                    completed_at=None,
                    duration_ms=0.0,
                    correlation_id=state.correlation_id,
                    error_category=None,
                )
            )
        return limited

    def _finish_audit(self, context: ToolExecutionContext, result: Result) -> None:
        with self.session_factory() as session, session.begin():
            row = session.scalar(
                select(ToolExecution)
                .where(
                    ToolExecution.id == result.execution_id,
                    ToolExecution.tenant_id == context.tenant_id,
                    ToolExecution.actor_id == context.user_id,
                    ToolExecution.outcome == "running",
                )
                .with_for_update()
            )
            if row is None:
                raise ToolError("audit_unavailable")
            row.outcome = result.status
            row.completed_at = result.completed_at
            row.duration_ms = result.duration_ms
            row.error_category = result.error.code if result.error else None

    def _run(self, state: RunState, identity: Identity) -> Result:
        code = None
        data = None
        context = None
        audited = False
        try:
            pending = None
            definition = None
            arguments = None
            try:
                definition = self.registry.resolve(
                    state.invocation.tool_name, state.invocation.tool_version
                )
                encoded = json.dumps(
                    state.invocation.arguments,
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                )
                if len(encoded.encode()) > 4096:
                    raise ToolError("arguments_too_large")
                arguments = definition.input_model.model_validate_json(
                    encoded, strict=True
                )
            except ToolError as exc:
                pending = exc
            except (ValidationError, ValueError, TypeError):
                pending = ToolError("invalid_arguments")
            with self.session_factory() as session:
                session.execute(text("SET TRANSACTION READ ONLY"))
                milliseconds = max(
                    1, int((definition.timeout_seconds if definition else 2.0) * 1000)
                )
                session.execute(
                    text("SELECT set_config('statement_timeout', :value, true)"),
                    {"value": str(milliseconds)},
                )
                session.execute(
                    text("SELECT set_config('lock_timeout', :value, true)"),
                    {"value": str(min(milliseconds, 500))},
                )
                context = self._context(session, identity, state)
                limited = self._begin_audit(context, state)
                audited = True
                if limited:
                    raise ToolError("rate_limited")
                if pending:
                    raise pending
                if state.stop.is_set():
                    raise ToolError(state.reason or "cancelled")
                if definition.required_permission not in context.permissions or (
                    state.required_permission is not None
                    and state.required_permission not in context.permissions
                ):
                    raise ToolError("permission_denied")
                scope = ReadScope.for_context(context, session, state.stop)
                raw = definition.handler(arguments, scope)
                scope.check_cancelled()
                try:
                    if isinstance(raw, BaseModel):
                        raw = raw.model_dump(mode="python")
                    if not isinstance(raw, dict):
                        raise ToolError("output_invalid")
                    output = definition.output_model.model_validate(raw, strict=True)
                    serialized = output.model_dump_json()
                    if len(serialized.encode()) > definition.max_result_bytes:
                        raise ToolError("result_too_large")
                    data = json.loads(serialized)
                except ValidationError:
                    raise ToolError("output_invalid") from None
                session.rollback()
        except ToolError as exc:
            code = exc.code
        except DBAPIError as exc:
            code = (
                "timeout"
                if getattr(exc.orig, "sqlstate", None) == "57014"
                else "database_unavailable"
            )
        except SQLAlchemyError:
            code = "database_unavailable"
        except Exception:
            code = "internal_error"
        # Serialize the final outcome against timeout/cancellation signals; no late success escapes.
        with state.lock:
            code = state.reason or code
            if (
                code is None
                and definition
                and monotonic() - state.clock > definition.timeout_seconds
            ):
                code = "timeout"
            state.finished = True
        result = state.result(code, data)
        if context is not None and audited:
            try:
                self._finish_audit(context, result)
            except Exception:
                logger.warning(
                    "tool_audit_unavailable",
                    extra={"request_id": str(state.correlation_id)},
                )
                return state.result("audit_unavailable")
        elif code is None or (context is not None and not audited):
            return state.result("audit_unavailable")
        return result

    def close(self) -> None:
        self.pool.shutdown(wait=True, cancel_futures=False)


@lru_cache
def get_tool_executor() -> ToolExecutor:
    return ToolExecutor()
