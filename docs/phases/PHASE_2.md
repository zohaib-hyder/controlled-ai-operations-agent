> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 2 completion report

Date: 2026-10-16. Scope: Enterprise Tool Registry and Validated Tool Contracts.

## 1. Implemented

Six version `1.0` read-only tools: `get_customer`, `get_account_status`, `get_ticket`, `list_customer_tickets`, `list_recent_transactions`, `search_policy`. Added immutable server context, strict input/output schemas, static registry, bounded executor, safe result envelopes, persisted metadata and rate limits, authenticated API and responsive authenticated Tool Explorer. No Phase 3 work, agent, LLM selection, approval execution or business writes.

## 2. Files created and modified

Created:
- `backend/app/tools/{__init__,contracts,context,errors,registry,handlers,executor}.py`
- `backend/app/api/tools.py`
- `backend/app/core/tool_body_limit.py`
- `backend/alembic/versions/0003_tool_execution.py`
- `backend/tests/test_tools.py`
- `frontend/src/app/tools/page.tsx`
- `frontend/src/lib/tools.ts`, `frontend/src/lib/tools.test.ts`
- `frontend/e2e/tools.spec.ts`
- `docs/architecture/TOOL_REGISTRY.md`, `TOOL_CONTRACTS.md`, `TOOL_SECURITY.md`
- `docs/decisions/0003-tool-execution.md`, this report.

Modified:
- `AGENTS.md`, `README.md`, `docs/architecture/OVERVIEW.md`
- `backend/app/main.py`, `backend/app/models/entities.py`, `backend/app/services/repository.py`
- `frontend/src/app/api/v1/[...path]/route.ts`, `frontend/src/app/globals.css`
- `frontend/src/lib/navigation.ts`, `frontend/src/lib/navigation.test.ts`
- `scripts/run_browser_tests.py` (explicit subprocess exit handling for Ruff).

## 3. Architecture decisions

Integration audit/strategy recorded before implementation in decision 0003. Reused existing authentication, role permission map, tenant repository, API errors and frontend session/proxy conventions. Explicit definitions bind trusted Python handlers and Pydantic models. Database read-only transactions add accidental-write protection; metadata writes use independent transactions. PostgreSQL advisory locking serializes persisted actor rate buckets. Frozen context is reconstructed from current server session and user, never client role/tenant arguments.

Migration revision `0003_tool_execution`, parent `0002_authentication`, adds tool execution metadata and tenant/actor rate buckets. No synthetic business schema changes were needed. Downgrade refuses destructive history loss. Ticket category/summary derive from existing fixtures. Policy keyword search is deterministic and parameterized. RLS remains deferred as documented in Phase 1.

## 4. Commands actually executed

From repository root unless indicated:

```sh
backend/.venv/bin/ruff format backend scripts
backend/.venv/bin/ruff check --config backend/pyproject.toml backend scripts
cd backend
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar .venv/bin/alembic upgrade head
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test .venv/bin/pytest -q
cd ../frontend
npm run lint
npm run typecheck
npm test
npm run build
npx --yes prettier@3.6.2 --write src/app/tools/page.tsx src/lib/tools.ts src/lib/tools.test.ts e2e/tools.spec.ts
cd ..
docker compose config --quiet
docker compose up -d --build backend frontend
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend python -m app.db.seed
docker compose exec -T backend python -m app.db.seed_auth
docker compose ps
PLAYWRIGHT_BROWSERS_PATH=/tmp/northstar-browsers backend/.venv/bin/python scripts/run_browser_tests.py
PYTHONPATH=backend backend/.venv/bin/python /tmp/phase2_live.py
docker compose run --rm -e TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@db:5432/northstar_test backend pytest -q -o cache_dir=/tmp/northstar-pytest-cache
git diff --check
```

A direct PostgreSQL count query also verified actual persisted counts: 2 tenants, 8 development users (6 base users plus 2 admins), 20 customers, 20 accounts, 30 tickets, 40 transactions, 10 policy-version records. The base seed command prints its 6-user manifest, not the 8-user authentication extension. Existing passwords were preserved. The temporary live-check script reads the ignored local password without printing it and issues authenticated HTTP requests through the frontend proxy.

## 5. Test results and failures

- Local backend: **133 passed**, including all 75 previous tests and 58 new tests. Migration/schema comparison, seed determinism/idempotency, permission denial, bidirectional tenant isolation, malicious evidence, strict contracts, output limits, SQL read-only enforcement, timeout, cancellation/capacity, audit, database failures, CSRF and shared rate limits covered.
- Container backend: **133 passed**, 1 Starlette deprecation warning (49.91 seconds).
- Ruff: passed with the repository configuration.
- Frontend lint and TypeScript: passed.
- Vitest: **10 passed** across 3 files (7 previous, 3 new).
- Production build: passed locally and in Docker.
- Playwright: **14 passed**, desktop/mobile, against the real local backend (10 previous, 4 new).
- Compose configuration, migration upgrade and seed commands: passed. All three services healthy.
- Live HTTP: customer 200, account 200, policy search 200, foreign customer 404, unknown tool 404, invalid UUID schema 422. Health/readiness both 200.

During development, the new result-byte test initially used a payload below the configured limit; the next fixture exceeded the name schema instead. Both runs had 132 passes and one failure. The final fixture is schema-valid and exceeds the byte limit; no security bounds were weakened. Initial frontend fixture typing and Ruff subprocess diagnostics were corrected. One backend warning remains: Starlette deprecates its current httpx TestClient integration. Playwright emitted harmless NO_COLOR/FORCE_COLOR warnings.

## 6. Security and reliability concerns

No critical tenant-isolation or authorization failure found in executed tests. Backend remains authoritative regardless of frontend validation. Auditors have the same read permissions for these six tools; tests separately verify they cannot list/execute a privileged definition. Audit payloads exclude arguments, customer results, SQL and credentials. Database/audit failures fail closed.

Timeouts cannot kill arbitrary synchronous Python. Workers are drained and slots retained until cleanup completes; statement/lock timeouts constrain built-in SQL. Audit/connection/cleanup latency can exceed the nominal handler deadline. Capacity rejection, malformed outer requests, unauthenticated requests and pre-context failures have no trusted execution row. Crashes/audit outages may leave running metadata. See TOOL_SECURITY.md for exact boundaries.

## 7. Remaining limitations

Trusted Python handlers are not sandboxed. Development database credentials are privileged, RLS is deferred, and metadata is not tamper-proof against database owners. Future operational work includes least-privilege DB roles, audit reconciliation/retention and deployment-level request deadlines. Existing frontend development dependency advisories from Phase 1 were not resolved with forced breaking upgrades. No production-readiness, external provider, hosted CI or external deployment claim.

## 8. Git

Phase 2 is committed locally after verification; identify the commit with `git log -1 --format=%H`. This report is part of that commit, so its own hash is intentionally not embedded. No push or external deployment. Final response records the exact hash and working-tree status.

## 9. Verdict

**PASS**. Local and container backend suites and all frontend/live verification checks passed. Phase 3 has not begun.
