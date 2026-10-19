import asyncio
import copy
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from functools import lru_cache
from time import monotonic
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from app.agents.checkpoints import (
    Counters,
    Snapshot,
    checkpoint_evidence_findings,
    minimize,
)
from app.agents.contracts import (
    TERMINAL,
    Evidence,
    Finding,
    Interpretation,
    InvestigationRequest,
    InvestigationResult,
    Limits,
    Plan,
    State,
    Step,
    transition,
)
from app.agents.planner import (
    ADVISORIES,
    AgentPlanner,
    DeterministicMockPlanner,
    LegacyDeterministicPlanner,
)
from app.agents.providers import PlannerFailure, configured_planner
from app.core.config import get_settings
from app.core.permissions import Identity
from app.schemas.planning import (
    DECISION,
    CallTool,
    Escalate,
    Finish,
    Insufficient,
    PlannerContext,
    SelectionTrace,
)
from app.services.evidence import EvidenceRetrievalService
from app.services.investigations import InvestigationRepository
from app.tools.errors import ToolError
from app.tools.executor import ToolExecutor, get_tool_executor


class Stop(Exception):
    def __init__(self, reason: str, state: State = State.FAILED):
        self.reason, self.state = reason, state


class AgentOrchestrator:
    def __init__(
        self,
        executor: ToolExecutor,
        planner: AgentPlanner | None = None,
        limits: Limits | None = None,
        repository: InvestigationRepository | None = None,
    ):
        self.executor = executor
        self.retrieval = EvidenceRetrievalService(executor)
        self.planner = planner or DeterministicMockPlanner()
        self.limits = limits or Limits()
        self.repository = repository or InvestigationRepository(
            executor.session_factory
        )
        self.active = 0

    def get(self, investigation_id: UUID, identity: Identity):
        return self.repository.get(identity, investigation_id)

    async def suggest_action(self, investigation_id, identity, correlation_id):
        """Bounded deterministic advisory proposal; explicit operator handoff only."""
        from app.schemas.actions import ProposalInput

        view = await asyncio.to_thread(self.get, investigation_id, identity)
        sources = [source for envelope in view.evidence for source in envelope.sources]
        account = next((s for s in sources if s.source_type == "account"), None)
        if account is None:
            raise HTTPException(409, "Account evidence required for suggestion")
        name = (
            "override_security_block"
            if account.facts.get("block_reason") == "security_review"
            else "request_account_reactivation"
        )
        references = tuple(
            s.evidence_id
            for s in sources
            if (
                s.source_type == "account"
                and s.source_resource_id == account.source_resource_id
            )
            or (
                s.source_type == "transaction"
                and s.facts.get("account_id") == str(account.source_resource_id)
            )
            or s.source_type == "policy"
        )
        proposal = ProposalInput(
            investigation_id=investigation_id,
            action_name=name,
            target_resource_id=account.source_resource_id,
            evidence_references=references,
            reason="Advisory proposal derived from structured account observations",
        )
        return await self.propose_action(
            investigation_id, identity, proposal, correlation_id
        )

    async def propose_action(
        self, investigation_id, identity, proposal, correlation_id
    ):
        """Explicit advisory handoff. Denials are persisted once, never retried."""
        from app.policies.engine import PolicyDecisionEngine
        from app.schemas.actions import ProposalInput

        body = ProposalInput.model_validate_json(proposal.model_dump_json())
        if body.investigation_id != investigation_id:
            raise HTTPException(422, "Proposal investigation mismatch")
        return await asyncio.to_thread(
            PolicyDecisionEngine(self.executor.session_factory).create,
            identity,
            body,
            correlation_id,
        )

    async def run(self, request, identity, correlation_id, *, idempotency_key=None):
        request = InvestigationRequest.model_validate_json(request.model_dump_json())
        investigation_id, created = await asyncio.to_thread(
            self.repository.create,
            identity,
            request,
            correlation_id,
            self.limits,
            idempotency_key,
            planner_type=self.planner.mode,
            planner_version=self.planner.planner_version,
            planner_config_hash=self.planner.config_hash,
        )
        if not created:
            return await asyncio.to_thread(self.get, investigation_id, identity)
        return await self._start(investigation_id, identity, recovery=False)

    async def resume(self, investigation_id, identity):
        return await self._start(investigation_id, identity, recovery=True)

    async def _start(self, investigation_id, identity, *, recovery):
        if self.active >= 4:
            raise HTTPException(
                429,
                "Investigation capacity exceeded; pending record is available in history",
            )
        self.active += 1
        try:
            claimed = await asyncio.to_thread(
                self.repository.claim, identity, investigation_id, recovery=recovery
            )
        except BaseException:
            self.active -= 1
            raise
        if claimed is None:
            self.active -= 1
            return await asyncio.to_thread(self.get, investigation_id, identity)
        return await self._execute(investigation_id, identity, claimed, recovery)

    async def _execute(self, investigation_id, identity, claimed, recovery):
        owner, version, restored, request, restored_evidence, corrupt = claimed
        limits = restored.limits
        planner = (
            LegacyDeterministicPlanner()
            if restored.planner_version == "1.0"
            and restored.planner_type == "deterministic_mock"
            else self.planner
        )
        planner_mismatch = (
            restored.planner_type != planner.mode
            or restored.planner_version != planner.planner_version
            or restored.planner_config_hash != planner.config_hash
        )
        traces = list(restored.tool_selection_trace)
        fingerprints = list(restored.observation_fingerprints)
        no_progress = restored.counters.no_progress
        provider_requests = restored.counters.provider_requests
        provider_tokens = restored.counters.provider_output_tokens_reserved
        provider_cost = restored.counters.provider_cost_microusd_reserved
        start = monotonic()
        base_elapsed = restored.counters.elapsed_ms / 1000
        correlation_id = restored.correlation_id
        history = list(restored.history)
        steps = list(restored.steps)
        evidence = list(restored_evidence)
        findings = checkpoint_evidence_findings(evidence)
        observations = copy.deepcopy(restored.observations)
        calls = restored.counters.tool_calls
        iterations = restored.counters.planning_iterations
        seen = Counter(restored.counters.repetitions)
        observation_size = restored.counters.observation_bytes
        plan = restored.plan
        event_sequence = restored.last_event_sequence
        pending_evidence = None
        attempted_step = None
        persistence_failed = False
        heartbeat_failed = False

        def elapsed():
            return base_elapsed + monotonic() - start

        async def heartbeat():
            nonlocal heartbeat_failed
            try:
                while True:
                    await asyncio.sleep(5)
                    await asyncio.to_thread(
                        self.repository.heartbeat, identity, investigation_id, owner
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                heartbeat_failed = True

        heartbeat_task = asyncio.create_task(heartbeat())

        def snapshot(phase):
            return Snapshot(
                planner_type=restored.planner_type,
                planner_version=restored.planner_version,
                planner_config_hash=restored.planner_config_hash,
                tool_selection_trace=tuple(traces),
                observation_fingerprints=tuple(fingerprints),
                state=history[-1],
                history=tuple(history),
                phase=phase,
                step_index=len(steps),
                plan_reference=investigation_id,
                plan=plan,
                steps=tuple(steps),
                completed_step_ids=tuple(
                    st.step_id for st in steps if st.status == "succeeded"
                ),
                counters=Counters(
                    provider_requests=provider_requests,
                    provider_output_tokens_reserved=provider_tokens,
                    provider_cost_microusd_reserved=provider_cost,
                    no_progress=no_progress,
                    tool_calls=calls,
                    planning_iterations=iterations,
                    observation_bytes=observation_size,
                    elapsed_ms=round(elapsed() * 1000, 3),
                    repetitions=dict(seen),
                ),
                limits=limits,
                observations=minimize(observations),
                evidence_ids=tuple(e.evidence_id for e in evidence),
                last_event_sequence=event_sequence,
                recovery_attempts=restored.recovery_attempts,
                recovery_error=restored.recovery_error,
                inflight_step=steps[-1].step_id
                if steps and steps[-1].status == "proposed"
                else None,
                correlation_id=correlation_id,
            )

        async def persist(phase, events=(), final=None):
            nonlocal version, event_sequence, pending_evidence
            try:
                version, saved = await asyncio.to_thread(
                    self.repository.save,
                    identity,
                    investigation_id,
                    owner,
                    version,
                    snapshot(phase),
                    list(events),
                    evidence=pending_evidence,
                    final=final,
                )
            except HTTPException as error:
                if error.status_code != 409:
                    raise
                current_version, _, cancelled = await asyncio.to_thread(
                    self.repository.load, identity, investigation_id
                )
                if not cancelled:
                    raise
                version = current_version
                if history[-1] not in {State.CANCELLED, State.FAILED}:
                    raise Stop(
                        "persistent_cancellation_requested", State.CANCELLED
                    ) from None
                version, saved = await asyncio.to_thread(
                    self.repository.save,
                    identity,
                    investigation_id,
                    owner,
                    version,
                    snapshot(phase),
                    list(events),
                    evidence=pending_evidence,
                    final=final,
                )
            event_sequence = saved.last_event_sequence
            pending_evidence = None

        async def check_cancellation():
            if heartbeat_failed:
                raise HTTPException(
                    409, "Execution heartbeat failed; explicit recovery required"
                )
            if await asyncio.to_thread(
                self.repository.cancellation_requested,
                identity,
                investigation_id,
                owner,
            ):
                raise Stop("persistent_cancellation_requested", State.CANCELLED)

        reason = "completed"
        recommendations = (
            "Request authorized human review before any operational action.",
        )
        uncertainty = (
            "Investigation incomplete; no eligibility or authorization decision was made.",
        )

        async def move(target):
            history.append(transition(history[-1], target))
            if target not in TERMINAL:
                await persist(
                    "state_changed",
                    [("planning_started", {})] if target == State.PLANNING else [],
                )

        def budget():
            if elapsed() >= limits.wall_seconds:
                raise Stop("wall_clock_limit", State.BUDGET_EXCEEDED)

        async def planning(method, *args):
            nonlocal iterations, provider_requests, provider_tokens, provider_cost
            budget()
            if iterations >= limits.planning_iterations:
                raise Stop("planning_iteration_limit", State.BUDGET_EXCEEDED)
            iterations += 1
            await check_cancellation()
            if planner.mode == "openai_compatible" and method.__name__ == "decide":
                tokens, cost = planner.reservation(args[1])
                if provider_requests >= limits.provider_requests:
                    raise Stop("provider_request_limit", State.BUDGET_EXCEEDED)
                if provider_tokens + tokens > limits.provider_output_tokens:
                    raise Stop("provider_token_limit", State.BUDGET_EXCEEDED)
                if provider_cost + cost > limits.provider_cost_microusd:
                    raise Stop("provider_cost_limit", State.BUDGET_EXCEEDED)
                provider_requests += 1
                provider_tokens += tokens
                provider_cost += cost
            await persist("planning")
            try:
                value = await asyncio.wait_for(
                    method(*copy.deepcopy(args)),
                    max(0.001, limits.wall_seconds - elapsed()),
                )
                budget()
                return value
            except TimeoutError:
                raise Stop("wall_clock_limit", State.BUDGET_EXCEEDED) from None
            except Stop:
                raise
            except PlannerFailure as exc:
                raise Stop(exc.reason) from None
            except Exception:
                raise Stop("planner_failure") from None

        def selected_ticket():
            tickets = observations.get("list_customer_tickets", {}).get("items", [])
            if request.ticket_id:
                return next(
                    (t for t in tickets if t["ticket_id"] == str(request.ticket_id)),
                    None,
                )
            return tickets[0] if tickets else None

        def trace(
            kind,
            outcome,
            *,
            proposed=None,
            execution_id=None,
            observation_id=None,
            evidence_ids=(),
            stop=None,
        ):
            traces.append(
                SelectionTrace(
                    iteration=iterations,
                    decision_type=kind,
                    summary=(
                        f"{outcome}: tool proposal {proposed.invocation.tool_name}"
                        if proposed
                        else f"{outcome}: {kind}"
                    ),
                    selected_tool=proposed.invocation.tool_name if proposed else None,
                    arguments_hash=hashlib.sha256(
                        json.dumps(
                            proposed.invocation.arguments,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode()
                    ).hexdigest()
                    if proposed
                    else None,
                    step_id=proposed.step_id if proposed else None,
                    tool_execution_id=execution_id,
                    observation_id=observation_id,
                    evidence_ids=tuple(evidence_ids),
                    validation_outcome=outcome,
                    stop_reason=stop,
                    budget_consumption={
                        "tool_calls": calls,
                        "planning_iterations": iterations,
                        "elapsed_ms": round(elapsed() * 1000, 3),
                        **(
                            {
                                "provider_requests": provider_requests,
                                "provider_output_tokens_reserved": provider_tokens,
                                "provider_cost_microusd_reserved": provider_cost,
                            }
                            if planner.mode == "openai_compatible"
                            else {}
                        ),
                    },
                    timestamp=datetime.now(UTC),
                )
            )

        def context():
            resources = {"customer_id": request.customer_id}
            ticket = selected_ticket()
            if ticket:
                resources["ticket_id"] = UUID(ticket["ticket_id"])
                resources["account_id"] = UUID(ticket["account_id"])
            value = PlannerContext(
                allowed_advisories=tuple(ADVISORIES.values()),
                goal=request.goal,
                resource_identifiers=resources,
                available_tools=tuple(
                    self.executor.registry.available(identity.permissions)
                ),
                completed_calls=tuple(
                    st.invocation for st in steps if st.status == "succeeded"
                ),
                observations=minimize(observations),
                evidence=tuple(src for item in evidence for src in item.sources),
                remaining_budgets={
                    "tool_calls": max(0, limits.max_tool_calls - calls),
                    "iterations": max(0, limits.planning_iterations - iterations),
                    "wall_seconds": max(0.0, limits.wall_seconds - elapsed()),
                    "provider_requests": max(
                        0, limits.provider_requests - provider_requests
                    ),
                    "provider_output_tokens": max(
                        0, limits.provider_output_tokens - provider_tokens
                    ),
                    "provider_cost_microusd": max(
                        0, limits.provider_cost_microusd - provider_cost
                    ),
                },
            )
            if (
                len(value.model_dump_json().encode())
                > get_settings().planner_context_bytes
            ):
                raise Stop("planner_context_limit", State.BUDGET_EXCEEDED)
            return value

        def validate_terminal(decision, ctx):
            known = {src.evidence_id for src in ctx.evidence}
            if not set(decision.evidence_ids) <= known:
                raise Stop("unsupported_citation", State.NEEDS_REVIEW)
            if isinstance(decision, Finish):
                for finding in decision.findings:
                    try:
                        self.retrieval.validate_finding(finding, ctx.evidence)
                        if finding.kind != "observed_fact":
                            raise ValueError(
                                "Provider interpretations are not verified facts"
                            )
                        if not set(finding.evidence_ids) <= set(decision.evidence_ids):
                            raise ValueError("Finding citations omitted")
                    except ValueError:
                        raise Stop("unsupported_finding", State.NEEDS_REVIEW) from None
                if not decision.findings and ctx.evidence:
                    raise Stop("unsupported_finding", State.NEEDS_REVIEW)

        def validate_step(proposed):
            if not isinstance(proposed, Step):
                raise Stop("invalid_plan")
            proposed = Step.model_validate_json(proposed.model_dump_json())
            if proposed.status != "proposed":
                raise Stop("invalid_plan")
            try:
                definition = self.executor.registry.resolve(
                    proposed.invocation.tool_name, proposed.invocation.tool_version
                )
                if (
                    definition.classification != "read"
                    or definition.required_permission not in identity.permissions
                ):
                    raise Stop("unauthorized_tool")
                args = definition.input_model.model_validate_json(
                    json.dumps(proposed.invocation.arguments), strict=True
                )
            except ToolError as exc:
                raise Stop(exc.code) from None
            except (ValidationError, ValueError, TypeError):
                raise Stop("invalid_tool_arguments") from None
            name = definition.name
            ticket = selected_ticket()
            # Investigation scope is narrower than the actor's tenant-wide read permission.
            if name in {"get_customer", "list_customer_tickets"}:
                valid = args.customer_id == request.customer_id
            elif name == "get_ticket":
                valid = (
                    ticket is not None and str(args.ticket_id) == ticket["ticket_id"]
                )
            elif name in {"get_account_status", "list_recent_transactions"}:
                valid = (
                    ticket is not None and str(args.account_id) == ticket["account_id"]
                )
            else:
                valid = name == "search_policy"
            if not valid:
                raise Stop("resource_outside_investigation")
            return proposed

        async def execute(proposed):
            nonlocal \
                calls, \
                observation_size, \
                pending_evidence, \
                no_progress, \
                attempted_step
            attempted_step = proposed
            await check_cancellation()
            budget()
            if len(steps) >= limits.max_steps:
                raise Stop("step_limit", State.BUDGET_EXCEEDED)
            if calls >= limits.max_tool_calls:
                raise Stop("tool_call_limit", State.BUDGET_EXCEEDED)
            proposed = validate_step(proposed)
            key = proposed.invocation.tool_name + json.dumps(
                proposed.invocation.arguments, sort_keys=True, separators=(",", ":")
            )
            if seen[key] >= limits.max_repeats:
                raise Stop("repeated_tool_call", State.BUDGET_EXCEEDED)
            if any(s.step_id == proposed.step_id for s in steps):
                raise Stop("duplicate_step_id")
            seen[key] += 1
            steps.append(proposed)
            calls += 1
            await persist(
                "before_tool",
                [
                    (
                        "tool_execution_started",
                        {
                            "step_id": proposed.step_id,
                            "tool_name": proposed.invocation.tool_name,
                            "decision_type": "CALL_TOOL",
                            "iteration": iterations,
                            "arguments_hash": hashlib.sha256(
                                json.dumps(
                                    proposed.invocation.arguments,
                                    sort_keys=True,
                                    separators=(",", ":"),
                                ).encode()
                            ).hexdigest(),
                        },
                    )
                ],
            )
            try:
                result = await asyncio.wait_for(
                    self.retrieval.retrieve(
                        proposed.invocation,
                        identity=identity,
                        correlation_id=correlation_id,
                    ),
                    max(0.001, limits.wall_seconds - elapsed()),
                )
            except TimeoutError:
                steps[-1] = proposed.model_copy(update={"status": "failed"})
                raise Stop("wall_clock_limit", State.BUDGET_EXCEEDED) from None
            if result.status != "success":
                trace(
                    "CALL_TOOL",
                    "failed",
                    proposed=proposed,
                    execution_id=result.execution_id,
                    stop="tool_" + result.error.code,
                )
                steps[-1] = proposed.model_copy(update={"status": "failed"})
                await persist(
                    "after_observation",
                    [
                        (
                            "tool_execution_completed",
                            {
                                "step_id": proposed.step_id,
                                "execution_id": str(result.execution_id),
                                "outcome": result.status,
                            },
                        )
                    ],
                )
                raise Stop("tool_" + result.error.code)
            data = result.data
            size = len(json.dumps(data, ensure_ascii=False).encode())
            if observation_size + size > limits.observation_bytes:
                steps[-1] = proposed.model_copy(update={"status": "failed"})
                raise Stop("observation_size_limit", State.BUDGET_EXCEEDED)
            observation_size += size
            observations[proposed.invocation.tool_name] = copy.deepcopy(data)
            steps[-1] = proposed.model_copy(update={"status": "succeeded"})
            name = result.tool_name
            reference = next(
                (
                    str(v)
                    for k, v in proposed.invocation.arguments.items()
                    if k.endswith("_id")
                ),
                "tenant-policy-search",
            )
            # Summaries use structured fields, never free-form instruction-bearing evidence text.
            if name == "get_account_status":
                summary = f"Account status: {data['status']}; block reason: {data['block_reason'] or 'none'}; evidence version: {data['evidence_version']}."
            elif name == "list_recent_transactions":
                unpaid = sum(t["status"] == "unpaid" for t in data["items"])
                summary = f"Observed {len(data['items'])} transactions; {unpaid} unpaid. This is a bounded ledger sample."
            elif name == "get_ticket":
                summary = f"Ticket status: {data['status']}; category: {data['category']}; duplicate reference: {data['duplicate_of_id'] or 'none'}. Ticket text remains untrusted."
            elif "items" in data:
                summary = f"Observed {len(data['items'])} schema-validated records. Text remains untrusted evidence."
            else:
                summary = "Customer ownership verified by tenant-scoped retrieval."
            references = []
            for row in data.get("items", []):
                resource = next(
                    (
                        str(v)
                        for k, v in row.items()
                        if k in {"ticket_id", "transaction_id", "policy_id"}
                    ),
                    None,
                )
                if resource:
                    references.append(
                        resource + (f":v{row['version']}" if "version" in row else "")
                    )
            item = Evidence(
                sources=EvidenceRetrievalService().normalize(
                    result,
                    investigation_id,
                    identity.tenant_id,
                    account=observations.get("get_account_status"),
                    ticket=observations.get("get_ticket"),
                ),
                evidence_id=uuid4(),
                tool_execution_id=result.execution_id,
                tool_name=name,
                tool_version=result.tool_version,
                source_reference=f"{name}:{reference}",
                source_references=tuple(references),
                summary=summary[:400],
                collected_at=result.completed_at,
            )
            semantic = {
                k: v for k, v in minimize({name: data})[name].items() if k != "limit"
            }
            fingerprint = hashlib.sha256(
                (
                    name + json.dumps(semantic, sort_keys=True, separators=(",", ":"))
                ).encode()
            ).hexdigest()
            if fingerprint in fingerprints:
                no_progress += 1
            else:
                fingerprints.append(fingerprint)
            trace(
                "CALL_TOOL",
                "executed",
                proposed=proposed,
                execution_id=result.execution_id,
                observation_id=item.evidence_id,
                evidence_ids=tuple(src.evidence_id for src in item.sources),
            )
            evidence.append(item)
            pending_evidence = item
            findings.append(
                Finding(text=item.summary, evidence_ids=(item.evidence_id,))
            )
            await persist(
                "after_observation",
                [
                    (
                        "tool_execution_completed",
                        {
                            "step_id": proposed.step_id,
                            "execution_id": str(result.execution_id),
                            "outcome": "success",
                        },
                    ),
                    ("evidence_collected", {"evidence_id": str(item.evidence_id)}),
                ],
            )
            attempted_step = None
            budget()
            if no_progress >= limits.max_no_progress:
                raise Stop("no_progress", State.BUDGET_EXCEEDED)

        try:
            if planner_mismatch:
                raise Stop("planner_configuration_mismatch")
            if corrupt:
                raise Stop("corrupt_checkpoint")
            await check_cancellation()
            if restored.inflight_step or any(st.status != "succeeded" for st in steps):
                raise Stop("interrupted_tool_requires_review", State.NEEDS_REVIEW)
            if history[-1] == State.CREATED:
                await move(State.PLANNING)
            budget()
            if plan is None:
                candidate = await planning(planner.initial_plan, request)
                if not isinstance(candidate, Plan):
                    raise Stop("invalid_plan")
                candidate = Plan.model_validate_json(candidate.model_dump_json())
                if tuple(st.invocation.tool_name for st in candidate.steps) != (
                    "get_customer",
                    "list_customer_tickets",
                ):
                    raise Stop("invalid_initial_plan")
                for candidate_step in candidate.steps:
                    validate_step(candidate_step)
                plan = candidate
                await persist(
                    "plan_validated", [("plan_validated", {"plan_version": "1.0"})]
                )
            if history[-1] == State.PLANNING:
                await move(State.RUNNING)
            for proposed in plan.steps:
                if proposed.step_id not in {
                    st.step_id for st in steps if st.status == "succeeded"
                }:
                    await execute(proposed)
            if not selected_ticket():
                raise Stop(
                    "ticket_not_in_bounded_customer_evidence"
                    if request.ticket_id
                    else "missing_ticket_evidence",
                    State.NEEDS_REVIEW,
                )
            final_proposal = None
            while True:
                ctx = context()
                decision = await planning(planner.decide, request, ctx)
                try:
                    encoded_decision = decision.model_dump_json()
                    if len(encoded_decision.encode()) > 16384:
                        raise Stop("planner_response_limit")
                    decision = DECISION.validate_json(encoded_decision, strict=True)
                except Stop:
                    raise
                except Exception:
                    raise Stop("invalid_planner_decision") from None
                if isinstance(decision, CallTool):
                    proposed = Step(
                        step_id=decision.step_id,
                        invocation=decision.invocation,
                        purpose=decision.purpose,
                        expected_evidence=decision.expected_evidence,
                    )
                    await execute(proposed)
                    continue
                validate_terminal(decision, ctx)
                trace(decision.kind, "validated", evidence_ids=decision.evidence_ids)
                await persist(
                    "planning",
                    [
                        (
                            "planner_decision",
                            {"type": decision.kind, "iteration": iterations},
                        )
                    ],
                )
                if isinstance(decision, Insufficient):
                    raise Stop(decision.reason, State.NEEDS_REVIEW)
                if isinstance(decision, Escalate):
                    reason = decision.reason
                    safe_planner = DeterministicMockPlanner()
                    escalation_classification = await safe_planner.interpret(
                        observations
                    )
                    supported_reasons = {"human_review_required"}
                    if escalation_classification.scenario == "security":
                        supported_reasons.add("security_review_required")
                    if (
                        escalation_classification.scenario == "conflict"
                        or self.retrieval.reconcile(
                            investigation_id, evidence
                        ).conflicts
                    ):
                        supported_reasons.add("conflicting_evidence")
                    cited = set(decision.evidence_ids)
                    supporting_sources = [
                        src
                        for envelope in evidence
                        for src in envelope.sources
                        if src.evidence_id in cited
                    ]
                    citation_support = True
                    if decision.reason == "security_review_required":
                        citation_support = any(
                            src.source_type == "account"
                            and src.facts.get("block_reason") == "security_review"
                            for src in supporting_sources
                        )
                    elif decision.reason == "conflicting_evidence":
                        conflicts = self.retrieval.reconcile(
                            investigation_id, evidence
                        ).conflicts
                        citation_support = any(
                            set(conflict.evidence_ids) <= cited
                            for conflict in conflicts
                        ) or any(
                            src.source_type == "account"
                            and src.facts.get("block_reason") == "conflicting_evidence"
                            for src in supporting_sources
                        )
                        if not citation_support:
                            citation_support = any(
                                account.source_type == "account"
                                and account.facts.get("block_reason")
                                == "resolved_billing"
                                and any(
                                    txn.source_type == "transaction"
                                    and txn.facts.get("status") == "unpaid"
                                    and txn.facts.get("account_id")
                                    == str(account.source_resource_id)
                                    for txn in supporting_sources
                                )
                                for account in supporting_sources
                            )
                    if decision.reason not in supported_reasons or not citation_support:
                        raise Stop("unsupported_escalation", State.NEEDS_REVIEW)
                    safe_advice = await safe_planner.recommend(
                        escalation_classification
                    )
                    if decision.required_follow_up not in safe_advice.next_steps:
                        raise Stop("unsupported_recommendation", State.NEEDS_REVIEW)
                    recommendations, uncertainty = (
                        safe_advice.next_steps,
                        safe_advice.uncertainty,
                    )
                    raise Stop(reason, State.NEEDS_REVIEW)
                final_proposal = decision
                break
            required = {
                "get_customer",
                "list_customer_tickets",
                "get_ticket",
                "get_account_status",
                "list_recent_transactions",
                "search_policy",
            }
            if not required.issubset(observations) or any(
                not observations[k]["items"]
                for k in ("list_recent_transactions", "search_policy")
            ):
                raise Stop("missing_evidence", State.NEEDS_REVIEW)
            account = observations["get_account_status"]
            if account["customer_id"] != str(request.customer_id):
                raise Stop("resource_outside_investigation")
            # Provider interpretation must agree with deterministic structured evidence classification.
            classification = await planning(planner.interpret, observations)
            authoritative = await DeterministicMockPlanner().interpret(
                copy.deepcopy(observations)
            )
            if (
                not isinstance(classification, Interpretation)
                or classification != authoritative
            ):
                raise Stop("ungrounded_interpretation", State.NEEDS_REVIEW)
            suggestion = await planning(planner.recommend, classification)
            safe = await DeterministicMockPlanner().recommend(authoritative)
            if suggestion != safe:
                raise Stop("unsupported_recommendation", State.NEEDS_REVIEW)
            if final_proposal and (
                final_proposal.advisory_recommendation != safe.next_steps
                or final_proposal.uncertainty != safe.uncertainty
            ):
                raise Stop("unsupported_recommendation", State.NEEDS_REVIEW)
            recommendations, uncertainty = safe.next_steps, safe.uncertainty
            if len(observations["list_customer_tickets"]["items"]) == 20:
                raise Stop("ticket_evidence_truncated", State.NEEDS_REVIEW)
            reconciliation = self.retrieval.reconcile(investigation_id, evidence)
            if reconciliation.conflicts and authoritative.scenario not in {
                "security",
                "conflict",
                "unknown",
            }:
                reason = "conflicting_evidence"
                await move(State.NEEDS_REVIEW)
            elif authoritative.scenario in {"security", "conflict", "unknown"}:
                reason = {
                    "security": "security_review_required",
                    "conflict": "conflicting_evidence",
                    "unknown": "unsupported_scenario",
                }[authoritative.scenario]
                await move(State.NEEDS_REVIEW)
            else:
                await move(State.COMPLETED)
        except asyncio.CancelledError:
            if steps and steps[-1].status == "proposed":
                steps[-1] = steps[-1].model_copy(update={"status": "failed"})
            await move(State.CANCELLED)
            reason = "request_cancelled"
            raise
        except Stop as stop:
            if steps and steps[-1].status == "proposed":
                steps[-1] = steps[-1].model_copy(update={"status": "failed"})
            await move(stop.state)
            reason = stop.reason
        except HTTPException:
            persistence_failed = True
            raise
        except Exception:
            if steps and steps[-1].status == "proposed":
                steps[-1] = steps[-1].model_copy(update={"status": "failed"})
            await move(State.FAILED)
            reason = "orchestration_failure"
        finally:
            trace(
                "STOP",
                "rejected"
                if reason
                in {
                    "unknown_tool",
                    "unsupported_version",
                    "unauthorized_tool",
                    "invalid_tool_arguments",
                    "resource_outside_investigation",
                    "repeated_tool_call",
                    "invalid_planner_decision",
                    "unsupported_finding",
                    "unsupported_citation",
                }
                else "stopped",
                proposed=attempted_step,
                stop=reason,
            )
            result = InvestigationResult(
                tool_selection_trace=tuple(traces),
                iteration_count=iterations,
                execution_limits=limits,
                reconciliation=EvidenceRetrievalService().reconcile(
                    investigation_id, evidence
                ),
                investigation_id=investigation_id,
                goal=request.goal,
                status=history[-1],
                history=tuple(history),
                steps=tuple(steps),
                evidence=tuple(evidence),
                findings=tuple(findings),
                recommended_next_steps=recommendations,
                uncertainty=uncertainty,
                stop_reason=reason,
                tool_calls_performed=calls,
                duration_ms=round(elapsed() * 1000, 3),
                human_review_recommended=True,
                correlation_id=correlation_id,
            )
            try:
                if not persistence_failed:
                    events = [
                        (
                            "budget_exceeded"
                            if result.status == State.BUDGET_EXCEEDED
                            else "investigation_completed"
                            if result.status in {State.COMPLETED, State.NEEDS_REVIEW}
                            else "investigation_cancelled"
                            if result.status == State.CANCELLED
                            else "investigation_failed",
                            {"stop_reason": reason},
                        )
                    ]
                    if recovery:
                        events.append(
                            (
                                "recovery_failed"
                                if corrupt or result.status == State.FAILED
                                else "recovery_completed",
                                {"stop_reason": reason},
                            )
                        )
                    try:
                        await persist("final", events, final=result)
                    except Stop:
                        history[-1] = State.CANCELLED
                        trace(
                            "STOP", "stopped", stop="persistent_cancellation_requested"
                        )
                        result = result.model_copy(
                            update={
                                "status": State.CANCELLED,
                                "tool_selection_trace": tuple(traces),
                                "history": tuple(history),
                                "stop_reason": "persistent_cancellation_requested",
                            }
                        )
                        await persist(
                            "final",
                            [
                                (
                                    "investigation_cancelled",
                                    {
                                        "stop_reason": "persistent_cancellation_requested"
                                    },
                                )
                            ],
                            final=result,
                        )
            finally:
                heartbeat_task.cancel()
                await asyncio.gather(heartbeat_task, return_exceptions=True)
                self.active -= 1
        return await asyncio.to_thread(self.get, investigation_id, identity)


@lru_cache
def get_orchestrator() -> AgentOrchestrator:
    settings = get_settings()
    return AgentOrchestrator(
        get_tool_executor(),
        planner=configured_planner(settings),
        limits=Limits(
            provider_requests=settings.llm_max_requests,
            provider_output_tokens=settings.llm_total_output_tokens,
            provider_cost_microusd=settings.llm_max_cost_microusd,
            max_steps=settings.agent_max_steps,
            max_tool_calls=settings.agent_max_tool_calls,
            wall_seconds=settings.agent_wall_seconds,
            max_repeats=settings.agent_max_repeats,
            observation_bytes=settings.agent_observation_bytes,
            planning_iterations=settings.agent_planning_iterations,
        ),
    )
