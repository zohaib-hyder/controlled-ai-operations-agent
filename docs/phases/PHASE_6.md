> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 6 — Dynamic tool selection and bounded multi-step execution

Date: 2026-10-17, Asia/Kolkata. Baseline: `private-baseline`. Scope: Phase 6 only. No business-changing actions, approval execution, paid verification, push, deployment or Phase 7.

## 1. What was implemented

Strict typed CALL_TOOL / FINISH / ESCALATE / STOP_INSUFFICIENT_EVIDENCE proposals; observation-driven deterministic selection and focused policy queries; an optional disabled-by-default OpenAI-compatible adapter; minimized bounded context; persisted request/token/configured-cost reservations; no-progress detection; source-linked operational traces; backward-compatible durable APIs/UI; 37 measured synthetic evaluation scenarios; and explicit live fixtures for rejection, cancellation and restart recovery.

Payment workflows inspect the ledger before policy; security/duplicate workflows retrieve focused policy first. A same-request regression changes account observations and proves the next selected tool changes. Six-read evidence coverage remains intact. Sources and all invocations still use the original authorization/executor/repository path.

Live evidence: [phase6-live-verification.json](assets/phase6-live-verification.json).

| Live check | Actual result |
| --- | --- |
| A payment | COMPLETED advisory; ledger before policy; six calls, eight planning iterations |
| B security | NEEDS_REVIEW; policy before ledger; ESCALATE/security_review_required |
| C duplicate | COMPLETED advisory; focused policy before corroborating ledger |
| D conflict | NEEDS_REVIEW; ESCALATE/conflicting_evidence |
| E invalid write-tool name | FAILED/unknown_tool before a third call; no business write |
| F repeated call | BUDGET_EXCEEDED/repeated_tool_call after two bootstrap reads |
| G cancellation | CANCELLED persists; zero calls |
| H actual backend restart/recovery | COMPLETED; original source IDs preserved; calls 2→6; customer executed once; nine charged planning iterations; one recovery attempt |
| I Phase 5 compatibility | Actual v1 history readable, six envelopes preserved, correct eight-iteration metadata |

Restart fixture H has an explicitly persisted 30-second wall budget (5,666.194 ms charged on the successful run), not a reset/default-budget override. The default runtime wall limit remains eight seconds. Invalid/repeated planners are trusted CLI-only synthetic verification fixtures, never an API parameter, public route or registered agent tool. Health/readiness succeeded and all three Compose services are healthy.

## 2. Files created and modified

Created:

- `backend/app/schemas/planning.py`
- `backend/app/agents/providers.py`
- `backend/tests/test_dynamic_planning.py`
- `frontend/next.config.ts`
- `scripts/aggregate_phase6_eval.py`, `scripts/verify_phase6.py`
- `docs/architecture/DYNAMIC_PLANNING.md`, `LLM_PLANNER.md`, `AGENT_TRACES.md`
- `docs/decisions/0007-dynamic-planning.md`
- `docs/evaluations/PHASE_6_AGENT_EVAL.md`, `phase6-cases.json`, `phase6-results.json`
- This report and `docs/phases/assets/phase6-live-verification.json`

Modified:

- `AGENTS.md`, `.env.example`, `.github/workflows/ci.yml`, `docker-compose.yml`, `README.md`
- `backend/app/agents/contracts.py`, `checkpoints.py`, `orchestrator.py`, `planner.py`
- `backend/app/core/config.py`, `logging.py`
- `backend/app/services/investigations.py`
- `backend/pyproject.toml`, `backend/uv.lock` (existing locked HTTPX becomes a runtime dependency; no dependency-version upgrade)
- `backend/tests/test_persistence.py`, `scripts/investigation_fixtures.py` (database-clock lease fixtures)
- `scripts/verify_phase5.py` (intentional import-location annotations for explicit CI Ruff configuration)
- `scripts/run_browser_tests.py` (forwards explicit Playwright CLI worker options; default behavior unchanged)
- `frontend/src/components/investigation-result.tsx`, `src/lib/investigations.ts`, `src/lib/evidence.test.tsx`, `e2e/investigations.spec.ts`
- `docs/architecture/OVERVIEW.md`, `DATA_MODEL.md`

## 3. Architecture decisions

[Decision 0007](../decisions/0007-dynamic-planning.md) was written before implementation. One orchestrator, executor and checkpoint path; no parallel authorization system. Trusted bootstrap establishes scope; later selection consumes actual structured observations. Backend registry/schema/RBAC/tenant/resource/budget/lease/session checks remain authoritative. Planner metadata is named separately from tool versions.

Additive strict JSON fields preserve schema version 1 and old history. New planner v2 is bound to durable metadata; legacy v1 recovery keeps its original selection order/query. Typed counter/limit defaults preserve historical checkpoint comparisons. Saves prevent budget resets, planner/config changes and trace-prefix rewriting. Completed steps are reused; ambiguous tool execution requires review. No new database migration; head remains **0005_policy_applicability**.

The optional provider uses a fixed environment-controlled HTTPS endpoint, bounded JSON output, no redirects/proxy environment/retries and safe error codes. Its requests and conservative output-token/configured-cost reservations are charged before the call, including failures. Keys/identities/prose are omitted from context. Model output cannot authorize anything. Final factual proposals require exact cited templates, and specific escalation reasons require the actual supporting source references; deterministic completeness/conflict/advisory validation controls finalization. No private chain-of-thought is stored.

Next build workers are capped at two on this approximately 3.8 GiB Docker host. Agent runtime limits were not relaxed. CI explicitly uses mock mode and emits an evaluation artifact; hosted CI itself was not run.

## 4. Commands actually executed

Repository root, unless working directory is specified:

```sh
# Dependency metadata: initial offline attempts failed, online resolution succeeded.
uv lock --project backend --offline
uv lock --project backend

# Infrastructure; final builds/startup succeeded.
docker compose config --quiet
docker compose build
docker compose run --rm backend alembic upgrade head
docker compose up -d --wait
docker compose build backend
docker compose up -d --wait backend
docker compose exec backend alembic current
docker compose run --rm backend python -m app.db.seed
docker compose ps

# Static checks, final runs passed.
backend/.venv/bin/ruff check --config backend/pyproject.toml backend scripts
backend/.venv/bin/ruff format --config backend/pyproject.toml --check backend scripts/aggregate_phase6_eval.py scripts/verify_phase6.py
git diff --check

# Repository root: final complete suite + measured case reports.
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test \
PHASE6_EVALUATION_DIR=/tmp/northstar-phase6-evaluation \
backend/.venv/bin/pytest -c backend/pyproject.toml backend/tests -xq

# Root: actual measurement aggregation and live HTTP/restart checks.
backend/.venv/bin/python scripts/aggregate_phase6_eval.py --input /tmp/northstar-phase6-evaluation
backend/.venv/bin/python scripts/verify_phase6.py --confirm-synthetic-local

# frontend/ working directory
npm run lint
npm run typecheck
npm test
npm run build

# Root: real browser suite, ignored credential loaded without logging.
PLAYWRIGHT_BROWSERS_PATH=/tmp/northstar-browsers \
backend/.venv/bin/python scripts/run_browser_tests.py --workers=1
```

Earlier targeted runs used `pytest tests/test_agents.py tests/test_persistence.py -xq` (145 passed) and `pytest tests/test_dynamic_planning.py -xq`. Four targeted recovery/corruption/partial-persistence/lease-loss cases passed after database-clock fixture changes. A one-off authenticated httpx read verified the actual Phase 5 record and added compatibility proof I. The live script executes `docker compose restart backend` and health/readiness requests. No paid provider call was made.

Configured-clone startup remains:

```sh
# First follow README .env and generated local demo-password instructions.
docker compose up -d db
docker compose build
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.db.seed
docker compose run --rm backend python -m app.db.seed_auth
docker compose up -d --wait
```

The auth seed above is startup guidance; the phase reused existing seeded local credentials. No credential value appears in tracked evidence.

## 5. Test results and failures

- **364 backend tests passed**, one upstream Starlette/httpx deprecation warning, **162.81 seconds**. Includes all Phase 0–5 regressions plus the new dynamic, security, provider-transport, budget and recovery checks.
- Ruff lint, format and whitespace checks passed.
- Frontend lint/typecheck passed; **15 Vitest tests passed** in five files.
- Local and Docker production frontend builds passed; final builds use two workers.
- **28 Playwright tests passed**, desktop/mobile, **53.2 seconds**, one browser worker. Actual planner mode/iterations/observation links, advisory evidence, cancellation, recovery, history and responsive layout were exercised. Desktop screenshot was visually inspected.
- Compose configuration/build/startup, unchanged migration head, synthetic seeding, live A–H and actual Phase 5 compatibility passed.
- [37-case measured evaluation](../evaluations/PHASE_6_AGENT_EVAL.md): dynamic next tools **48/48**; full sequences **12/12**; expected safe outcomes **37/37**; advisory task completion **18/18**; grounded factual records **343/343**; unauthorized proposals blocked **6/6**; loops terminated **4/4**; escalation correctness **4/4**; unsupported findings **0**; tenant leakage **0**. Ten runs ended in COMPLETED; deliberate review/failure/budget/cancellation/recoverable outcomes are not misreported as autonomous business successes.

Resolved attempts: offline uv resolution lacked cache access/packages; normal locked resolution succeeded without version upgrades. Duplicate trace rows exceeded the existing 24 KiB sample-response assertion; compact single completion records retained pre-dispatch metadata in existing step/events without weakening the assertion. A test planner's tool-version attribute collided with new metadata; separate planner_version fixed it and adversarial regressions passed. A settings override helper used duplicate keyword arguments and was corrected. The initial crash fixture raised a planner error (correctly handled as planner_failure); it was replaced by a real committed-checkpoint/disconnect fault. One expected-success run correctly reached its wall guard during simultaneous heavy builds; final verification was sequential. Lease-expiry fixtures now use PostgreSQL time rather than requiring host/VM clock alignment. An overlong build was interrupted, then two-worker builds completed. Initial test-file edits used the wrong working directory and were corrected before final checks. CLI Ruff annotations were aligned with CI configuration.

The first live restart fixture correctly stopped with wall_clock_limit: approximately 20.846 seconds of elapsed/downtime against eight seconds. A new, explicitly bounded 30-second synthetic fixture then demonstrated successful recovery while charging downtime and preserving counters. The old terminal budget result was not resumed or rewritten. A final four-worker browser rerun returned 26 passes and two correct wall-clock budget stops under host load. The complete suite was then rerun with one browser worker, keeping runtime budgets and every assertion unchanged. No blanket retry or rate-limit reset was used. No unresolved test failure remains.

## 6. Security and reliability concerns

Observed tenant leakage, unauthorized business writes, fabricated evidence, unsupported returned factual findings and uncontrolled loops: **none** in the executed synthetic checks. Read-tool registry constraints, live session/RBAC revalidation, tenant ownership, narrower investigation scope, lease fencing, cancellation, strict arguments, idempotency and immutable evidence remain in place. Tests cover role/session revocation during planning, untrusted source instructions, forged context, unknown/write-capable tool requests, invalid versions/arguments, malformed/oversized/refused provider output, unsupported facts/citations/escalation reasons and unrelated escalation references, provider/tool/database failures and before/after-commit persistence faults.

No secrets, raw provider replies or private reasoning are recorded. Cost/token fields are conservative configured reservations, not billing measurements. Database owners remain privileged; ORM append-only checks/hashes are not external tamper-proof storage or PostgreSQL RLS. Existing synchronous-tool cleanup may exceed nominal timeout while draining safely. Live verification uses synthetic local actors/data only. No push/deployment occurred.

## 7. Remaining limitations

The paid provider is **live-unverified**; only injected transports and deterministic mock execution were tested. Model/provider protocol support, output reliability and billing must be verified separately before enabling. Configured rates/tokenizer assumptions bound reservations but do not attest arbitrary vendor metering. Deterministic planning is domain bounded over six tools with two fixed ownership/discovery reads; it adapts order/query from structured observations and does not parse source prose as instructions. The finite synthetic evaluation is an acceptance set, not a production success estimate. Default eight-second wall bounds may intentionally stop work under host load or restart downtime. Legacy records gain no invented trace/backfill. No new retention policy, RLS, distributed workers, operational eligibility, approvals or writes are implemented. Phase 7 was not started.

## 8. Git status and commit

All Phase 6 code, fixtures, tests, CI changes, documentation and actual measured evidence are included in the local Phase 6 commit. The exact hash is supplied in the final completion response (a commit cannot embed its own hash). Final status is checked after commit. No push or deployment.

## 9. Verdict

**PASS** for the requested synthetic Phase 6 scope. Required local checks, adverse cases and actual restart recovery passed. This does not certify production readiness, live paid-provider behavior or operational action authority.
