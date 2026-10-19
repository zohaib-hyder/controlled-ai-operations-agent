> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 9 completion report

## 1. Implemented

PostgreSQL execution jobs, attempts, append-only events/dead letters; strict submission/status contracts; explicit legal lifecycle; authenticated enqueue and bounded listing; fenced leased worker; current session-independent submitter authority; existing controlled execution reuse; classified bounded backoff; receipt reconciliation; authorized cancellation/manual retry; submission backpressure and global/per-tenant capacity; local database breaker and structured operational metrics; Execution Jobs UI; synthetic failure evaluation and runbook.

No Phase 10, security overrides, autonomous agent writes, external business integrations, paid dependency, push or deployment.

## 2. Files

- `.env.example`
- `.github/workflows/ci.yml`
- `AGENTS.md`
- `README.md`
- `backend/alembic/versions/0008_durable_jobs.py`
- `backend/app/api/jobs.py`
- `backend/app/core/logging.py`
- `backend/app/core/permissions.py`
- `backend/app/core/tool_body_limit.py`
- `backend/app/execution/service.py`
- `backend/app/jobs/authority.py`
- `backend/app/jobs/contracts.py`
- `backend/app/jobs/metrics.py`
- `backend/app/jobs/service.py`
- `backend/app/jobs/worker.py`
- `backend/app/main.py`
- `backend/app/models/entities.py`
- `backend/app/services/authentication.py`
- `backend/tests/test_durable_jobs.py`
- `docker-compose.yml`
- `docs/architecture/DURABLE_JOBS.md`
- `docs/architecture/EXECUTION_RECONCILIATION.md`
- `docs/architecture/OVERVIEW.md`
- `docs/architecture/RETRY_POLICY.md`
- `docs/architecture/WORKER_RELIABILITY.md`
- `docs/decisions/0010-durable-execution-jobs.md`
- `docs/evaluations/PHASE_9_RELIABILITY.md`
- `docs/evaluations/phase9-results.json`
- `docs/phases/PHASE_9.md`
- `docs/phases/assets/phase9-live-verification.json`
- `frontend/e2e/jobs.spec.ts`
- `frontend/src/app/api/v1/[...path]/route.ts`
- `frontend/src/app/execution-jobs/page.tsx`
- `frontend/src/lib/jobs.test.ts`
- `frontend/src/lib/jobs.ts`
- `frontend/src/lib/navigation.ts`
- `scripts/aggregate_phase9_eval.py`
- `scripts/verify_phase9.py`

## 3. Architecture decisions

Migration `0008_durable_jobs` follows `0007_controlled_execution` and adds four tenant-scoped tables. One mutation path remains: ControlledActionExecutor. Internal durable identity comes from authenticated persisted submission, never a fabricated worker service role. Current actor permission, exact proposal/command/request binding, PDP/evidence/resource versions, original approval and leased ownership are revalidated. Submitter cookie expiry is independent of job authority; reviewer grant/session validation is preserved.

A short advisory-lock-protected SKIP LOCKED claim enforces four global/one tenant concurrent jobs. Leases are 30 seconds with monotonic fences; the executor holds the job row through its SERIALIZABLE transaction and bounds its mutation by lease expiry. No sleeping transactions or generic broker. See decision 0010 and the four Phase 9 architecture documents.

## 4. Commands actually executed

```sh
docker compose config --quiet
docker compose build backend frontend worker
docker compose up -d db
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.db.seed_auth
docker compose up -d --wait backend frontend
docker compose build backend worker
docker compose run --rm backend alembic current
docker compose run --rm backend alembic check
docker compose up -d --wait worker
docker compose logs --tail=2 worker
docker compose stop worker
docker compose ps -a --format json worker
docker compose start worker
docker compose ps
curl --fail --silent http://localhost:8000/api/v1/health
curl --fail --silent http://localhost:8000/api/v1/ready
```

The migration was generated locally with Alembic autogenerate and reviewed before applying; its generated revision was renamed to the sequential `0008_durable_jobs` identifier. Test runs use only disposable `northstar_test`:

```sh
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test \
PHASE9_EVALUATION_DIR=/tmp/northstar-phase9-evaluation \
backend/.venv/bin/pytest -c backend/pyproject.toml backend/tests -xq

TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test \
PHASE9_EVALUATION_DIR=/tmp/northstar-phase9-evaluation \
backend/.venv/bin/pytest -c backend/pyproject.toml backend/tests/test_durable_jobs.py -xq

TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test \
PHASE9_EVALUATION_DIR=/tmp/northstar-phase9-evaluation \
backend/.venv/bin/pytest -c backend/pyproject.toml backend/tests/test_durable_jobs.py backend/tests/test_controlled_execution.py -xq

TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test \
backend/.venv/bin/pytest -c backend/pyproject.toml backend/tests --ignore=backend/tests/test_durable_jobs.py -q

backend/.venv/bin/python scripts/aggregate_phase9_eval.py --input /tmp/northstar-phase9-evaluation
backend/.venv/bin/ruff check --config backend/pyproject.toml backend scripts
backend/.venv/bin/ruff format --config backend/pyproject.toml --check backend scripts
```

Frontend `npm run lint`, `npm run typecheck`, `npm test -- --run` and `npm run build` were executed from `frontend/`. Live checks used:

```sh
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar \
backend/.venv/bin/python scripts/verify_phase9.py --confirm-synthetic-local

DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar \
backend/.venv/bin/python scripts/prepare_phase8_browser.py --confirm-synthetic-local
PHASE8_BROWSER_FIXTURE_PATH=/tmp/northstar-phase8-browser.json \
PLAYWRIGHT_BROWSERS_PATH=/tmp/northstar-browsers \
backend/.venv/bin/python scripts/run_browser_tests.py --workers=1
```

## 5. Results and failures

The intermediate Phase 9 suite passed **68 tests in 145.36 seconds**. All **512 prior-phase regression tests passed in 475.45 seconds**. Each run reported one upstream Starlette/httpx deprecation warning. The expanded final job/executor suite passed **109 tests in 194.86 seconds**: **74 job tests plus 35 repeated executor checks**. This verifies **586 unique backend tests** across the final regression/focused runs (512 + 74); the 35 executor checks were intentionally rerun after the narrow retry change. Final A–J live checks passed again on the rebuilt image, including a queued job retained across one worker-process exit and completed by a fresh process. **All 38 Playwright desktop/mobile tests passed in 1.4 minutes**, with no skips. The previously budget-limited desktop case passed unchanged during the serial run. Completed evaluation: **55/55 expected outcomes**, comprising **50 injected-failure scenarios plus five controls**; recovery **20/20**, reconciliation **15/15**, retry classification **10/10**, dead letters **5/5**, cancellation **5/5**, duplicate/unauthorized mutation cases **0/55 each**, cross-tenant route leakage **0/5**. Live A–J passed. Alembic head `0008_durable_jobs`; no schema drift. Synthetic auth seed preserved existing passwords. Frontend lint/typecheck and 29 Vitest tests passed; local and Docker production builds passed. Final health returned `ok`; readiness returned `ready`. PostgreSQL, backend and frontend are healthy; the worker is running and emits structured metrics. Its graceful Compose stop exited with code **0**, followed by a successful restart. Final Alembic head/drift checks passed again.

Failures found and addressed:

Intermediate backend runs (stopped with `-x`): 0 passed/1 failed (redundant lock); 25 passed/1 failed (unrelated-policy expectation); 3 passed/1 failed (restricted fixture during concurrent builds); isolated restricted rerun 1 passed; 273 passed/1 failed (conflicting scheduling fixture); 15 passed/1 failed (invalid expired-session fixture). Final successful runs supersede those failures. Initial Ruff formatting/import findings were corrected; no ignored checks or disabled assertions.

- A final audit found savepoint SQL serialization errors were previously converted to permanent FAILED receipts. Known rollback states now propagate to the bounded worker retry path; an actual PostgreSQL partial-write serialization test verifies full rollback and one eventual mutation.
- Initial durable evidence lookup tried to lock an actor already locked by the outer executor transaction; removed redundant read-side lock while retaining executor locks. No mutation committed.
- Matrix initially expected unrelated operational policy changes to deny note actions. Expectations now follow actual applicability: note actions stay eligible; three restricted policy-bound actions deny.
- A restricted fixture was temporarily ineligible during concurrent builds; isolated rerun passed without changing policy checks or runtime budgets.
- Broader run stopped at 273 passed/1 failed because a scheduling-capacity test used the deliberately conflicting customer-4 scenario. Scheduling tests now use eligible customer-3 proposals; conflict denial is preserved.
- Browser run: 35 passed/1 failed; desktop investigation safely stopped at its eight-second wall budget (8.38s) while backend tests ran. The mobile equivalent passed. The final serial run passed all 38 tests; no budget increase or assertion weakening.
- An evaluation aggregation attempt correctly rejected an incomplete matrix while tests were still running. It succeeded only after all required case artifacts existed.
- A fast isolated run exposed an invalid expired-session fixture (expiry before creation); expiry is now creation plus one microsecond, already past at execution, preserving the database constraint.
- A README read and npm invocation were attempted from the wrong repository subdirectory; both failed without file changes and were rerun from the correct directories.

## 6. Security and reliability concerns

No additional mutation path. No authorization from AI. No caller-supplied scheduling/tenant/role/fence fields accepted. Tenant composite FKs and scoped access prevent foreign references. Expired/revoked approval, current actor deactivation/demotion, stale evidence/policy/resource facts and prohibited actions fail closed. Duplicate keys and proposal bindings do not grant repeat mutation. Uncertain outcomes remain explicit until atomic evidence proves a result.

Workers have privileged queue discovery but no service-role business authority. Database-owner SQL tampering is outside application ORM append-only guarantees. No raw tokens or customer contents in job metadata/logs. Structured transition logs may precede rollback; persisted events are authoritative.

## 7. Limitations

Local synthetic PostgreSQL writes only; no external exactly-once claim. Fixed safety caps and bounded transactions suit this portfolio demonstration, not a throughput or production-readiness claim. No distributed breaker, production alerting, multi-region failover, backup recovery or automatic ambiguous-evidence repair. Ambiguous jobs remain visible and unclaimable. Worker leases are not renewed indefinitely; stalled work loses authority. UI uses a bounded first page, explicit proposal/decision/approval IDs and explicit refresh. The demo intentionally retains two ambiguous-consumption fixtures in RECONCILIATION_REQUIRED and two exhausted fixtures in DEAD_LETTERED from the two live verification runs; the worker does not blindly execute them. Hosted GitHub Actions were configured but not run here.

## 8. Git

Baseline `private-baseline`. Phase 9 is committed locally after successful verification; the final commit identifier is returned in the completion response and available via `git log -1`. No push/deployment.

## 9. Verdict

**PASS** — Phase 9 implemented and locally verified. No Phase 10 started.
