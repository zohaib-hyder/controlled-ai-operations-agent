> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 4 completion report

Date: 2026-10-17. Baseline: `private-baseline`.

## 1. Implemented

PostgreSQL-backed investigation state, ordered steps, versioned bounded checkpoints, append-only application events, evidence and final results. Added transactional state/version checks, actor/tenant/payload-bound idempotency, database-time leases/heartbeat, explicit conservative recovery, durable cancellation, owner-scoped history APIs and refresh-safe history/detail UI. Existing six tools remain read-only; every actual call still passes through ToolExecutor. No Phase 5, business-changing tools, approval execution, distributed worker infrastructure or real enterprise integrations.

## 2. Files created and modified

Created:
- `backend/alembic/versions/0004_persistent_investigations.py`
- `backend/app/agents/checkpoints.py`, `persistence_contracts.py`
- `backend/app/services/investigations.py`
- `backend/tests/test_persistence.py`
- `frontend/src/components/investigation-history.tsx`, `investigation-result.tsx`
- `frontend/src/app/investigations/[investigationId]/page.tsx`
- `frontend/e2e/persistence.spec.ts`
- `scripts/investigation_fixtures.py`
- `docs/architecture/INVESTIGATION_PERSISTENCE.md`, `CHECKPOINTS.md`, `RECOVERY.md`
- `docs/decisions/0005-investigation-persistence.md`, this report and `docs/phases/assets/phase4-live-verification.json`.

Modified:
- `AGENTS.md`, `README.md`, `.github/workflows/ci.yml`
- `backend/app/agents/orchestrator.py`, `backend/app/api/investigations.py`
- `backend/app/core/tool_body_limit.py`, `backend/app/main.py`, `backend/app/models/entities.py`
- `backend/app/services/authentication.py`, `backend/app/tools/executor.py`
- `backend/tests/test_agents.py`
- `frontend/src/app/api/v1/[...path]/route.ts`, `frontend/src/app/globals.css`
- `frontend/src/app/investigations/page.tsx`, `frontend/src/lib/investigations.ts`
- `frontend/e2e/investigations.spec.ts`, `scripts/run_browser_tests.py`
- `docs/architecture/OVERVIEW.md`, `DATA_MODEL.md`, `AGENT_ORCHESTRATION.md`, `AGENT_EVIDENCE.md`.

## 3. Architecture decisions

The pre-implementation audit and integration design are in decision 0005. Migration revision `0004_persistent_investigations` (parent `0003_tool_execution`) adds the five lifecycle tables and a composite tool-execution unique constraint for tenant-bound evidence FKs. Business data, policies and sessions are preserved. No new runtime dependency or infrastructure service.

The repository is the lifecycle write boundary. Current session/role revalidation is shared with ToolExecutor. History is tenant- and creating-actor-scoped. Parent locks plus expected versions fence writes; consistent detail reads lock the parent while reading checkpoint children. State transitions/events/checkpoints and final results commit atomically. Creation uses canonical payload hashes, scoped unique keys and transaction advisory locks. Missing idempotency headers retain compatibility with fresh generated keys, while the UI supplies/reuses keys for unchanged payloads.

Recovery acquisition uses an owner UUID, 120-second database-clock expiry, heartbeat every five seconds and version/owner/expiry checks. Completed observations restore without replay; any recorded unfinished step stops NEEDS_REVIEW. Original budgets and elapsed downtime are retained. Corrupt checkpoints produce a durable corruption marker before final failure, so a second crash during recovery cannot erase that decision. Cancellation is durable and terminal records never restart. Checkpoint bodies omit unused source prose/session secrets and are capped at 131072 bytes. See the three architecture documents for exact boundaries.

## 4. Commands actually executed

Major commands (repeated verification rounds are summarized in section 5):

```sh
# backend/ working directory
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar .venv/bin/alembic revision --autogenerate --rev-id 0004_persistent_investigations -m 'Persistent investigations and fenced checkpoints'
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar .venv/bin/alembic upgrade head
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test .venv/bin/pytest tests/test_agents.py -q -x
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test .venv/bin/pytest tests/test_persistence.py tests/test_agents.py -q
# repository root
backend/.venv/bin/ruff format backend scripts
backend/.venv/bin/ruff check --config backend/pyproject.toml backend scripts
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test backend/.venv/bin/pytest -q
# frontend/ working directory
npx --offline --yes prettier@3.6.2 --write e2e/persistence.spec.ts
npm run lint
npm run typecheck
npm test
npm run build
# repository root
docker compose config --quiet
docker compose up -d --build backend frontend
docker compose up -d --build backend
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend alembic current
docker compose exec -T backend python -m app.db.seed
docker compose exec -T backend python -m app.db.seed_auth
PLAYWRIGHT_BROWSERS_PATH=/tmp/northstar-browsers backend/.venv/bin/python scripts/run_browser_tests.py
PYTHONPATH=backend backend/.venv/bin/python /tmp/phase4_live.py create
docker compose restart backend
PYTHONPATH=backend backend/.venv/bin/python /tmp/phase4_live.py verify
PYTHONPATH=backend backend/.venv/bin/python /tmp/phase4_live.py recover
docker compose run --rm -e TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@db:5432/northstar_test backend pytest -q -o cache_dir=/tmp/northstar-pytest-cache
git diff --check
```

The autogenerated migration was reviewed, its composite tool unique constraint moved before the evidence FK, renamed clearly and its destructive downgrade refused. Formatter also ran on the new frontend components/routes and changed existing files. Live scripts use the ignored local password without printing it. Browser lifecycle fixtures authenticate a fictional reviewer on loopback and create only synthetic investigation metadata; they are explicitly restricted to development/test. CI setup was updated to provide those fixture UUIDs, but hosted CI is not claimed to have run.

## 5. Results and development failures

- Final local backend: **277 passed**, 1 existing Starlette/httpx deprecation warning, in 110.74 seconds. Includes 240 retained/adapted regression cases and 37 Phase 4 cases.
- Frontend lint and TypeScript: passed. Vitest: **13 passed**, four files. Local production build and Docker production build: passed.
- Final Playwright: **26 passed** in 31.6 seconds, including all 20 prior cases plus six desktop/mobile persistence cases. Verified actual history/filter/detail navigation, refresh persistence, events/evidence, cancellation and incomplete-tool recovery. Desktop/mobile detail screenshots were visually inspected.
- Compose validation/build and migration upgrade/current: passed; head `0004_persistent_investigations`. Actual seed counts: 2 tenants, 8 users, 20 customers, 20 accounts, 30 tickets, 40 transactions, 10 policy-version records. The base seed CLI prints its six-user manifest; auth seeding adds two admins and preserves passwords.
- Live restart: created **af5b4c02-e884-41ad-8cb9-7a1d1a9c5713**, COMPLETED, checkpoint 26, 26 events, six evidence records. Restarted the backend container, authenticated again, and asserted full result/events/evidence equality. Same key/payload returned the existing result; changed payload returned 409. Cross-tenant result/events/evidence requests all returned 404.
- Live recovery: **17abfecd-080c-45fe-9a5d-b0671c3ecb41** had one completed tool and an expired lease. Authenticated resume completed with six total calls, recovery attempt 1, checkpoint 25; first evidence **de809c9a-434a-4095-b8a3-2d1f2e6b95fb** was preserved. A tenant/actor/correlation-scoped database count confirmed **get_customer executed exactly once**. See the machine-readable proof in assets/phase4-live-verification.json for IDs, counts and restart comparison hashes.
- Final Docker backend: **277 passed**, 1 existing deprecation warning, in 90.69 seconds. All three final Compose services are healthy. Health/readiness succeeded during the real authenticated restart workflow.

Intermediate successful runs included 107 orchestration cases, 273 full backend cases locally and in Docker, then 275 and 276 full local cases as integrity coverage expanded. The original 240 regression cases remain covered; obsolete process-expiry/capacity assertions were adapted to durable recreation/bounded pagination, and foreign/missing reference assertions now verify pre-insertion 404. Stale-role rejection now happens before creation with 403. These are intentional stronger admission/durability semantics, not relaxed tenant checks.

Development failures were corrected rather than bypassed:
- Initial focused regression stopped at 75 passes/1 failure because a foreign customer now correctly fails admission; related foreign/deleted ticket assertions were adapted. A subsequent run had 105 passes/2 failures: a deleted optional ticket fixture and an invalid planner value entering checkpoint serialization. Missing-evidence tests now omit the deleted optional reference, and only validated plans are persisted. The next orchestration run passed all 107.
- Combined persistence/orchestration run had 128 passes/1 failure exposing the missing cancel/resume body-size guard. The guard now enforces 8192 bytes before parsing on those routes too.
- Frontend lint caught synchronous effect state updates; loading state now derives from request completion and clears errors on actual responses.
- First 26-case browser run passed 24 with two old status selectors also matching the new history filter. Assertions now target the investigation-result region.
- One focused 35-case run was mistakenly overlapped with the container suite against the same disposable test database and hit 35 setup conflicts. It is not counted as a passing run. Subsequent final verification runs are sequential; no application check was weakened to hide the setup collision.
- Routine import/format diagnostics and an initial directory-relative checkpoint file creation were corrected. Existing Starlette/httpx deprecation and Playwright NO_COLOR/FORCE_COLOR warnings remain.

## 6. Security and reliability findings

Tenant/actor isolation, current-session permission checks, composite FKs, idempotency uniqueness, lease fencing, optimistic conflicts, event/checkpoint uniqueness and application append-only behavior are tested. Final results must agree with independently persisted evidence and state; integrity disagreement fails closed. Corrupt checkpoint recovery does not dispatch tools. No business mutation or approval execution capability was introduced. Source text is untrusted and unused prose is omitted from checkpoints. No raw session token, password or session ID is persisted there.

Direct PostgreSQL owners can still alter history; checksums and application guards are not tamper-proof signatures. RLS/least-privilege deployment roles remain deferred. Explicit fixture corruption/lease expiry uses privileged test/setup access, never an agent tool or public API.

## 7. Remaining limitations

Execution remains request-scoped, with local admission bounds and database ownership across limited instances. There is no distributed scheduler, automatic restart recovery, exactly-once claim for arbitrary external effects, or hard Python thread termination. A late old read can finish its tool audit after lease loss but cannot publish a stale observation. Downtime consumes the wall budget, so long interruptions normally exhaust the budget. An ambiguous in-flight tool stops for review even if it never actually started. Cancellation cannot forcibly kill blocking work and HTTP disconnect is not reliable task cancellation.

Retention/archiving, reconciliation, deployment least privilege and RLS are future operational work. Old Phase 3 in-memory results cannot be recovered if they were lost before migration. Current observations are bounded samples/separate snapshots and recommendations remain advisory. No production-readiness, real-provider or hosted-CI claim. Phase 5 has not begun.

## 8. Git

A local Phase 4 commit is created only after final verification. The report is part of that commit; retrieve the exact hash with `git log -1 --format=%H`. The final response records the hash and working-tree status. No push or external deployment.

## 9. Verdict

**PASS**. Final local/container backend suites, frontend static/unit/build checks, all browser cases, migration/seed/Compose checks and real restart/recovery verification passed. No critical tenant-isolation, state-corruption or unsafe duplicate-execution failure remains.
