> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 3 completion report

Date: 2026-10-16. Baseline commit: `private-baseline`.

## 1. Implemented

A controlled read-only investigation orchestrator using all six existing enterprise tools. Added typed finite state machine, provider-neutral async planner, deterministic mock scenario planning, plan/resource validation, bounded execution, evidence provenance, evidence-grounded summaries and advisory recommendations. Authenticated creation/retrieval endpoints and an Investigation Workspace expose actual terminal states, timeline, tool calls, evidence, findings, uncertainty and stop reasons. No Phase 4, business writes, approvals, persistent recovery or full LLM provider integration.

## 2. Files created and modified

Created:
- `backend/app/agents/contracts.py`, `planner.py`, `orchestrator.py`
- `backend/app/api/investigations.py`
- `backend/tests/test_agents.py`
- `frontend/src/lib/investigations.ts`, `investigations.test.ts`
- `frontend/e2e/investigations.spec.ts`
- `docs/architecture/AGENT_ORCHESTRATION.md`, `AGENT_STATE_MACHINE.md`, `AGENT_EVIDENCE.md`
- `docs/decisions/0004-agent-orchestration.md`, this report.

Modified:
- `.env.example`, `AGENTS.md`, `README.md`, `docker-compose.yml`
- `backend/app/core/config.py`, `backend/app/core/tool_body_limit.py`, `backend/app/main.py`
- `backend/app/tools/executor.py` (optional trusted additional permission checked using current server context)
- `frontend/src/app/investigations/page.tsx`, `frontend/src/app/globals.css`, `frontend/src/app/api/v1/[...path]/route.ts`
- `docs/architecture/OVERVIEW.md`.

## 3. Architecture decisions

The integration audit was recorded in decision 0004 before implementation. Reused authentication/RBAC, tenant repositories, ToolExecutor, strict contracts, audit metadata and frontend proxy/shell. No business schema changes or new infrastructure/dependencies. Migration head remains `0003_tool_execution`.

An explicit transition table governs CREATED → PLANNING → RUNNING → terminal states, with invalid edges and all transitions out of terminal states rejected. Strict plans bootstrap customer ownership and bounded ticket discovery; subsequent resource IDs must match the selected customer-linked ticket. Every evidence retrieval calls ToolExecutor directly and rechecks live investigation permission plus the tool's permission.

Planner observations are copied. Structured evidence classification and an allowlisted advisory mapping constrain interpretation/recommendations. Goals and source prose cannot select tools or permissions. Default budgets are 8 steps, 8 tool calls, 8 seconds, 1 identical call, 48,000 observation bytes and 8 planner invocations. Four investigations and four tool workers bound concurrency. Results expire after 15 minutes and are limited to 100 per process, bound to tenant and creating actor. This is temporary result retrieval, not checkpoint recovery.

## 4. Commands actually executed

```sh
backend/.venv/bin/ruff format backend scripts
backend/.venv/bin/ruff check --config backend/pyproject.toml backend scripts
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test backend/.venv/bin/pytest -q backend/tests/test_agents.py
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test backend/.venv/bin/pytest -q
cd frontend
npx --yes prettier@3.6.2 --write src/app/investigations/page.tsx src/lib/investigations.ts src/lib/investigations.test.ts
npx --offline --yes prettier@3.6.2 --write e2e/investigations.spec.ts
npm run lint
npm run typecheck
npm test
npm run build
cd ..
docker compose config --quiet
docker compose up -d --build backend frontend
docker compose up -d --build backend
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend alembic current
docker compose up -d --build frontend
PLAYWRIGHT_BROWSERS_PATH=/tmp/northstar-browsers backend/.venv/bin/python scripts/run_browser_tests.py
PYTHONPATH=backend backend/.venv/bin/python /tmp/phase3_live.py
PYTHONPATH=backend backend/.venv/bin/python /tmp/phase3_fault_live.py
docker compose run --rm -e TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@db:5432/northstar_test backend pytest -q -o cache_dir=/tmp/northstar-pytest-cache
git diff --check
```

The live scripts used ignored demo credentials without printing them. The first used the real running frontend/backend HTTP API. The fault harness started and stopped temporary loopback Uvicorn on port 8001 with server-only dependency overrides: one-step budget, then a deliberately invalid planner. These are not public request overrides or enabled product features. No external system was contacted for business data.

## 5. Test results and failures

- Local backend: **240 passed**, 1 existing Starlette/httpx deprecation warning; includes all 133 previous tests plus 107 Phase 3 cases. Covers all state-pair transitions, six scenarios, permissions, tenant isolation, forged identities, prompt injection, no account mutations, budgets, repetition, cancellation during planning and an actual tool, planner/tool/database failures, provenance and temporary-store isolation/retention/capacity.
- Container backend: **240 passed**, 1 existing deprecation warning (236.04 seconds).
- Ruff passed.
- Frontend lint/typecheck passed; Vitest **13 passed**, 4 files (10 previous + 3 new).
- Playwright final rerun: **20 passed** (14 previous + 6 new), desktop/mobile, in 31.8 seconds. Desktop/mobile screenshots were visually inspected; horizontal overflow assertions passed. The new service-error display case uses a controlled HTTP 503 mock; successful evidence and security escalation use the real backend.
- Local and Docker production builds passed. All three final Compose services are healthy. Compose configuration validation and migration upgrade/current passed; head remains `0003_tool_execution`.
- Live real API: blocked account COMPLETED with 6 calls/6 evidence records; security hold NEEDS_REVIEW/security_review_required with 6/6; foreign customer FAILED/tool_not_found with 1 call/0 evidence. Owner-scoped GET matched returned results. Every finding referenced collected evidence. Health/readiness returned 200.
- Live fault configuration: BUDGET_EXCEEDED/step_limit retained 1 evidence record; FAILED/unknown_tool retained 2 bootstrap records and did not execute the unknown tool.

Development failures were investigated and corrected: initial focused suite had 96 passes/2 failures (JSON UUID bridge and a test registry attribute typo); next focused run passed 98. A broader run had 236 passes/1 timing-sensitive test failure because an injected exception shared a 20ms timeout; its exception case now uses the normal tool deadline while the separate timeout test retains a short deadline. Final local suite passed all 240. The first browser run had 16 passes/4 new form cases failing to locate the wrapped select's exact label; explicit accessible control names were added. Initial formatter invocation without network access failed, then succeeded with authorized access; a directory-relative formatting attempt was corrected. No validation/security checks were bypassed. A second browser run had 15 passes/5 failures while container checks competed for resources; this exposed a generic alert selector matching the Next.js announcer and a 5-second result assertion shorter than the 8-second investigation budget, plus slow sign-in assertions. New result waits now allow 15 seconds and the alert selector targets the expected error text. Application deadlines and security limits were unchanged; the final browser rerun is recorded below.

## 6. Security and reliability concerns

No critical authorization, fabricated evidence or unauthorized business-write failure was found in passing backend/live checks. Caller role/tenant/context overrides are rejected; auditor creation is forbidden. ToolExecutor remains authoritative, including current investigation permission on every call. Cross-tenant resources yield no evidence. Ticket/policy prompt injection does not drive planning. Audit metadata contains no raw goals, observation payloads or credentials.

Synchronous trusted Python cannot be forcibly killed. Deadlines are cooperative, database statements have existing timeouts, and cancellation drains workers; connection/audit/cleanup latency may exceed the nominal wall limit. Client disconnect may not cancel ASGI execution. Results are transient, process-local and inaccessible across workers/restarts. Tool metadata persists, but there is no durable investigation lifecycle ledger. RLS/least-privilege deployment roles remain deferred.

## 7. Remaining limitations

Only deterministic mock planning is configured; token/cost usage is zero because there is no LLM call. No autonomous writes, approval execution, eligibility certification, policy engine, durable background worker, checkpoint recovery or public cancellation endpoint. Investigations use bounded ticket/ledger samples and separate tool snapshots; evidence may change between calls and is not an atomic business snapshot. Unknown, missing, truncated or conflicting evidence stops for human review. Existing dependency advisories and development DB-owner audit mutability from prior phases remain. No production readiness or hosted CI claim.

## 8. Git

Local Phase 3 commit is created only after final verification. This report is included in that commit; retrieve its exact hash with `git log -1 --format=%H`. The final response records the commit hash and working-tree status. No push or external deployment.

## 9. Verdict

**PASS**. All final backend, frontend, browser, migration/Compose and live investigation checks passed. No critical authorization failure, fabricated evidence or unauthorized business write was observed. Phase 4 has not begun.
