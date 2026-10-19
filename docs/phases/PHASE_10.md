> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 10 — Operations Command Center

Date: 2026-10-18. Baseline: `private-baseline`. Scope is Phase 10 only.

## 1. Implemented

Authenticated database-derived operational overview, bounded UTC filters, rates and duration summaries, current backlog gauges, normalized timeline, stored-reference correlation lookup, deterministic incident discovery, response state machine, configurable alerts and safe pipeline health. Responsive overview/operations, incident and diagnostics pages use real APIs and display empty/error states accurately. No agent execution semantics or business mutation handlers were added.

## 2. Files created and modified

| Files | Purpose |
| --- | --- |
| `backend/app/operations/{contracts,service,incidents,worker}.py` | Strict DTOs, metrics/timeline/correlation, incident lifecycle/detection, private worker observations |
| `backend/app/api/operations.py`, `app/main.py`, `app/core/tool_body_limit.py` | Authenticated bounded API registration and request limits |
| `backend/app/models/entities.py`, `backend/alembic/versions/0009_operations.py` | Incident/config/rate/worker persistence, composite tenant FKs and operational indexes |
| `backend/app/jobs/worker.py` | Successful poll observations and bounded periodic detection |
| `backend/tests/test_operations.py` | 52 new backend tests including 40 evaluation scenarios |
| `frontend/src/components/{operations,diagnostics}.tsx`, `src/lib/operations.ts` | Typed real-data UI and diagnostic traces |
| `frontend/src/app/{page.tsx,operations/page.tsx,incidents/page.tsx,incidents/[id]/page.tsx,diagnostics/page.tsx}` | Command Center, incident response and diagnostics routes |
| `frontend/src/app/api/v1/[...path]/route.ts`, `src/lib/navigation{,.test}.ts` | Exact proxy allowlist and role-aware navigation |
| `frontend/src/lib/operations.test.tsx`, `frontend/e2e/operations.spec.ts` | 13 unit tests and 10 desktop/mobile browser cases |
| `scripts/{aggregate_phase10_eval,prepare_phase10_browser,verify_phase10}.py` | Evaluation aggregation and guarded synthetic live verification |
| `.github/workflows/ci.yml` | Evaluation artifacts and fresh synthetic browser fixtures |
| `AGENTS.md`, `README.md`, `docs/architecture/OVERVIEW.md` | Phase scope, startup and architecture updates |
| `docs/architecture/{OPERATIONS_COMMAND_CENTER,OBSERVABILITY,INCIDENT_MANAGEMENT,CORRELATION_TRACING}.md` | Source audit, definitions, security boundaries, runbooks and limits |
| `docs/decisions/0011-operations-command-center.md` | Architecture decision |
| `docs/evaluations/{PHASE_10_OPERATIONS.md,phase10-results.json}`, `docs/phases/assets/phase10-live-verification.json`, this report | Actual evidence and phase record |

## 3. Architecture decisions

Reuse PostgreSQL and existing persisted workflow records; no broker or paid monitoring service. Migration `0009_operations` follows `0008_durable_jobs`. Consistent REPEATABLE READ snapshots use SQL aggregates and bounded union timelines; rate accounting occurs in a separate small transaction with identity revalidation in both transactions. Statement/lock timeouts and selective indexes constrain work. Operators see their own workflow metadata; reviewers/admins/auditors see tenant metadata. Backend permissions remain authoritative.

Creation cohorts use half-open UTC ranges, custom intervals at most 31 days. Current backlog gauges intentionally ignore creation filters. Empty denominators and duration samples are null. Success is completed jobs divided by completed+failed+dead-lettered jobs; uncertain/cancelled outcomes are excluded. Approval turnaround uses the first approved/rejected decision. See OBSERVABILITY for every denominator.

Incidents follow OPEN → ACKNOWLEDGED → INVESTIGATING → RESOLVED → CLOSED, with direct acknowledged→resolved allowed. Reviewer/admin responses append incident and security events transactionally. Unique tenant/condition keys deduplicate discovery. Responses never retry jobs or mutate business resources. Correlation follows stored IDs/references only; inaccessible or absent graphs return 404. Links use scoped diagnostics rather than weakening legacy content permissions.

## 4. Commands actually executed

From the repository root unless stated otherwise:

```sh
docker compose config --quiet
docker compose build backend frontend worker
docker compose stop worker
docker compose up -d db
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.db.seed_auth
docker compose up -d --wait backend frontend worker
docker compose run --rm backend alembic check

# Disposable northstar_test database, from backend/:
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test .venv/bin/alembic downgrade 0008_durable_jobs
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test .venv/bin/alembic upgrade head
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test .venv/bin/alembic check

# Root; isolated test DB:
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test PHASE10_EVALUATION_DIR=/tmp/northstar-phase10-evaluation backend/.venv/bin/pytest -c backend/pyproject.toml backend/tests/test_operations.py -q
backend/.venv/bin/python scripts/aggregate_phase10_eval.py --input /tmp/northstar-phase10-evaluation
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test backend/.venv/bin/pytest -c backend/pyproject.toml backend/tests --ignore=backend/tests/test_operations.py -q
backend/.venv/bin/ruff check --config backend/pyproject.toml backend scripts
backend/.venv/bin/ruff format --check --config backend/pyproject.toml backend scripts

# frontend/:
npm run lint
npm run typecheck
npm test -- --run
npm run build

# Root; explicit synthetic local fixtures:
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar backend/.venv/bin/python scripts/prepare_phase10_browser.py --confirm-synthetic-local
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar backend/.venv/bin/python scripts/verify_phase10.py --confirm-synthetic-local
```

Local startup is the first Compose block, after creating the ignored `.env` using README configuration instructions. Worker startup follows migrations. Verification scripts read the ignored local credential without logging it. Fixture preparation performs one actual verified synthetic note, three actual retry-exhaustion jobs and an explicitly injected ambiguous outcome; it is not a real customer integration.

## 5. Test results and failures

New backend suite: 52 passed in the final rerun in 80.48 seconds. The full baseline regression rerun: 586 passed in 516.55 seconds. Together these cover 638 unique backend tests. Frontend unit suite: 42 passed. Final Playwright rerun: 48 passed (24 desktop, 24 mobile), zero skips, in 1.1 minutes. Frontend lint/typecheck and Ruff passed on final sources. Local production build and Docker images built successfully. Migration round trip and schema drift check passed. All A–J authenticated live checks passed with zero unsafe business mutations. Public health returned `{"status":"ok"}` and readiness returned `{"status":"ready"}`. Seed verification found 2 tenants, 21 customers, 21 accounts, 31 tickets, 40 transactions and 10 policies in the existing synthetic demo, including earlier phase fixtures.

Evaluation: metrics 40/40, detection 40/40, deduplication 40/40, permitted correlation 36/36, scoped reads 40/40, incident mutation authorization 4/4, foreign correlation denials 4/4, alerts 40/40, cross-tenant leaks 0/4, unsafe business mutations 0/40. Denominators and individual cases are in the evaluation report.

During development an own-login audit event invalidated an overly broad empty-timeline assertion; the assertion now checks actor/tenant scope. One added test initially lacked a UUID import. Frontend lint caught synchronous state updates in effects; loading state was refactored without disabling the rule. Navigation expectations were updated for the three new authorized read pages. These failures were corrected and the affected suites rerun successfully. The first full baseline regression run returned 583 passed and three approval-eligibility failures in resource-change evaluation cases. A targeted rerun of all five resource-change cases passed (47 deselected). No authorization or eligibility checks were weakened. The full rerun passed all 586 tests. The transient cause was not established. The first browser run returned 44 passed/4 failed: a cleanup edit had removed the required dead-letter backlog DTO field (restored), and a diagnostics selector matched timeline links as well as related-record links (scoped to the related-record section). The complete operations suite and browser suite were rerun after correction. An upstream Starlette/httpx deprecation warning remains.

## 6. Security and reliability concerns

Strict schemas, current backend identity revalidation, tenant predicates/composite FKs, CSRF, bounded pagination/time windows, rate limits and append-only application events protect the new API. No raw evidence, session token, secret or credential is included in generated timeline summaries. User notes remain bounded escaped text and reject obvious credential assignments; users must still avoid entering secrets. Existing deterministic policy, approval binding, fencing, reconciliation and write idempotency remain authoritative.

Incident response and metrics reads were checked against unchanged business snapshots and source job states. Unknown/stale workers never show as healthy. Database outage prevents a private snapshot and produces an unavailable UI, rather than stale healthy cards. Worker observations expose aggregate infrastructure availability only.

## 7. Remaining limitations

Local synthetic/mock evidence does not establish production readiness. Hosted CI was configured but not executed here. No external alert delivery, production load/retention study or Phase 11 work. ORM append-only history does not defend against database-owner SQL. Worker observation is not instance attestation. Closed incidents do not reopen automatically for the same source condition; persistent backlog alerts remain. Traces cap graph roots/links and timeline events and explicitly report truncation. Historical creation cohorts show current snapshot statuses, not reconstructed historical state. No changes to stricter legacy content endpoint permissions. Incident detail displays the latest 25 persisted events; a dedicated history pagination endpoint is not included.

## 8. Git status and commit

Final local commit and status are recorded in the completion response. No push or external deployment was performed; Docker services run locally only.

## 9. Verdict

**PASS** — Phase 10 scope completed with final passing backend, frontend, migration, Docker and live verification. No evaluated cross-tenant leak, unauthorized incident mutation, fabricated metric or unsafe business action was observed. Initial failures and the unresolved transient regression-test cause are disclosed above; these local results do not establish production readiness.


## Additional commands executed

```sh
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar backend/.venv/bin/python scripts/prepare_phase8_browser.py --confirm-synthetic-local
PHASE10_BROWSER_FIXTURE_PATH=/tmp/northstar-phase10-browser.json PHASE8_BROWSER_FIXTURE_PATH=/tmp/northstar-phase8-browser.json PLAYWRIGHT_BROWSERS_PATH=/tmp/northstar-browsers backend/.venv/bin/python scripts/run_browser_tests.py --workers=1
docker compose run --rm backend alembic current
curl --fail --silent http://localhost:8000/api/v1/health
curl --fail --silent http://localhost:8000/api/v1/ready
git diff --check
```

The full baseline rerun also used `--tb=short`. Targeted reproduction used `backend/tests/test_execution_eval.py -k resource -q` with the same TEST_DATABASE_URL and pytest configuration: 5 passed, 47 deselected. Final backend/worker images were rebuilt after the response-schema correction. Seed verification queried counts with local `docker compose exec -T db psql -U northstar -d northstar`; it did not reset existing demo records.
