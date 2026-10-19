> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 8 — human approvals and controlled execution

## 1. Implemented

Durable independent human approvals, explicit state transitions, current authorization and PDP revalidation, five allowlisted local write handlers, single-use approval consumption, transactional idempotency, optimistic resource updates, verified execution receipts and human-facing review/execution UI. Agent/tool execution capabilities remain read-only. No override handler, external write integration, paid dependency or Phase 9.

## 2. Files

New execution service/schema/API, migration 0007, approval/execution/business models, 52-case evaluation and targeted security tests, live/browser fixture verifiers, approval queue/detail/controlled-action components, architecture documentation and CI evaluation/browser configuration. Full changed-path list is recorded at completion.

## 3. Architecture

See decision 0009 and architecture documents. SERIALIZABLE transactions, tenant advisory serialization, locked live actors/reviewers/resources, existing deterministic PDP and a database-time optimistic UPDATE guard precede every mutation. Savepoint rollback isolates mutation/verification failures. Final receipts, business effects, audit and approval consumption commit together. Database uniqueness prevents repeat execution; ambiguous commit errors require same-key reconciliation.

## 4. Commands

Commands actually executed (repository root unless noted):

```sh
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test \
  PHASE7_EVALUATION_DIR=/tmp/northstar-phase7-evaluation \
  PHASE8_EVALUATION_DIR=/tmp/northstar-phase8-evaluation \
  backend/.venv/bin/pytest -c backend/pyproject.toml backend/tests -xq
backend/.venv/bin/ruff check --config backend/pyproject.toml backend scripts
backend/.venv/bin/ruff format --config backend/pyproject.toml --check backend scripts
docker compose config --quiet
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar \
  backend/.venv/bin/alembic -c backend/alembic.ini check
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar \
  backend/.venv/bin/python scripts/verify_phase8.py --confirm-synthetic-local
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar \
  backend/.venv/bin/python scripts/prepare_phase8_browser.py --confirm-synthetic-local
PHASE8_BROWSER_FIXTURE_PATH=/tmp/northstar-phase8-browser.json \
  PLAYWRIGHT_BROWSERS_PATH=/tmp/northstar-browsers \
  backend/.venv/bin/python scripts/run_browser_tests.py --workers=1
curl --fail --silent http://127.0.0.1:8000/api/v1/health
curl --fail --silent http://127.0.0.1:8000/api/v1/ready
backend/.venv/bin/python scripts/aggregate_phase8_eval.py --input /tmp/northstar-phase8-evaluation
backend/.venv/bin/python scripts/aggregate_phase7_eval.py --input /tmp/northstar-phase7-evaluation
git diff --check
```

From frontend: `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`. Targeted pytest runs preceded the full regressions. Both images were actually built; Compose waited for healthy services. Alembic reported no schema drift. No credential values were logged.

 Startup with the ignored local environment configured:

```sh
docker compose up -d db
docker compose build backend frontend
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.db.seed_auth
docker compose up -d backend frontend
```

## 5. Results and failures

Final backend regression: **512 passed**, one upstream Starlette/httpx deprecation warning, **363.52 seconds**. This includes all previous regressions and 87 Phase 8 checks. No final failures.

Measured 52-case security evaluation:

| Metric | Actual |
|---|---:|
| Authorized execution success | 15/15 |
| Unauthorized execution blocked | 19/19 |
| Self-approval blocked | 2/2 |
| Stale approval blocked | 9/9 |
| Duplicate business mutation cases | 0/5 |
| Cross-tenant mutation cases | 0/5 |
| Security overrides | 0/4 |
| Outcome verification accuracy | 52/52 |
| Critical unsafe mutation cases | 0/52 |

The separate concurrent replay test also asserted exactly one business record. Positive evaluation cases compare all affected business rows against an explicit target whitelist, not just the returned success flag. Phase 7 evaluation remained 41/41 with zero unsafe eligibility decisions and 10/10 stale rejections.

Completed checks:

- Frontend lint/typecheck and local/Docker production builds passed. Vitest **24/24**.
- Final-image Playwright **34/34**, **47.9 seconds**, desktop and mobile, including independent approval/rejection/execution and before/after/audit/error views.
- Targeted 74 initial execution/evaluation tests passed; seven final HTTP/identity/recovery checks passed; three final protected-field/kind rollback and lost-response checks passed.
- Live A–J passed: customer note, ticket note, reactivation request, account reactivation and duplicate closure committed and verified; self-approval 403; foreign execution 404; expired approval DENIED; same-key replay returned the same execution with zero extra effects; security override DENY. Critical unsafe mutations observed: 0.
- Health and database readiness passed; all three Compose services healthy. Migration `0007_controlled_execution` applied; model/schema drift check passed; standard development authentication seed preserved existing credentials.

Resolved failures and interrupted attempts:

- Autogenerated migration initially placed the new composite receipt uniqueness after dependent foreign keys and emitted an unnamed-constraint warning. Reviewed and corrected ordering and explicit constraint name before applying; upgrade and drift check passed.
- The previous system test expected the absent approvals route to return 404. It now correctly expects authenticated endpoint denial (401). Exact permission expectations were explicitly extended for the new separate capabilities.
- A full regression run was intentionally interrupted after 382 passes to load strengthened verifier code. This left disposable fixture records; the next targeted run detected duplicate admin fixtures. Only the `_test` database was cleared using existing teardown semantics, then the targeted checks passed. No demo/customer database was cleared.
- Initial browser run: 29 passed, 5 failed. Error locator also matched Next.js route announcer; fixture setup changed legacy policy freshness; mobile receipt grid overflowed. Fixed the locator, isolated Phase 8 fixtures to tenant 1 with a dedicated synthetic executor, restored the original tenant-0 policy timestamps, and constrained grid widths. Full 34-test rerun passed without changing runtime budgets, weakening freshness assertions or purging rate limits.
- The last policy audit found duplicate-ticket policy applicability needed the live parent account state. Added parent ownership/binding/state evaluation and two allowed/denied boundary tests; both passed, followed by the complete 512-test run and refreshed A–J live proof.
- Ruff import/format errors during implementation were corrected. No failed final check is accepted.

## 6. Security and reliability

Execution is creator-only, operator/admin permission only, and human-requested. Independent reviewer/admin approval is required for restricted actions. Current permissions and session revocation are checked at execution. No ALLOW automatically executes. Security overrides have no handler. Audit and verification failures never yield a success response.

## 7. Limitations

Synthetic local database only; no production-readiness claim. Application-level immutable history does not protect against privileged SQL. No RLS, external tamper-evident audit, distributed executor or external write integration. Hosted CI was configured but not run; no paid provider calls were made. Conservative serializable conflicts require retry with the same key. If storage is inaccessible at ambiguous commit, a durable uncertainty record cannot be guaranteed; the response explicitly requires reconciliation. Approval is bounded by the original receipt expiry and original reviewer session validity. Request/pending queue expiry is resolved on detail/decision/execution.

## 8. Git

All verification completed before the local Phase 8 commit. The final response records its hash; `git log -1 --format=%H` retrieves it. No push or external deployment.

## 9. Verdict

**PASS** for Phase 8 synthetic controlled execution. No unauthorized or cross-tenant mutation, successful self-approval, duplicate business mutation or security override occurred in the tested cases. Phase 9 was not started.

## Complete changed paths

- `.github/workflows/ci.yml`
- `AGENTS.md`
- `README.md`
- `backend/alembic/versions/0007_controlled_execution.py`
- `backend/app/api/execution.py`
- `backend/app/core/permissions.py`
- `backend/app/core/tool_body_limit.py`
- `backend/app/execution/service.py`
- `backend/app/main.py`
- `backend/app/models/entities.py`
- `backend/app/policies/engine.py`
- `backend/app/schemas/execution.py`
- `backend/app/services/investigations.py`
- `backend/tests/test_authentication.py`
- `backend/tests/test_controlled_execution.py`
- `backend/tests/test_execution_eval.py`
- `backend/tests/test_policy_engine.py`
- `backend/tests/test_system.py`
- `docs/architecture/APPROVAL_WORKFLOWS.md`
- `docs/architecture/AUTHORIZATION.md`
- `docs/architecture/CONTROLLED_EXECUTION.md`
- `docs/architecture/EXECUTION_RECEIPTS.md`
- `docs/architecture/OVERVIEW.md`
- `docs/decisions/0009-controlled-execution.md`
- `docs/evaluations/PHASE_8_EXECUTION_EVAL.md`
- `docs/evaluations/phase8-results.json`
- `docs/phases/PHASE_8.md`
- `docs/phases/assets/phase8-live-verification.json`
- `frontend/e2e/approvals.spec.ts`
- `frontend/src/app/action-proposals/approval/[id]/page.tsx`
- `frontend/src/app/action-proposals/page.tsx`
- `frontend/src/app/api/v1/[...path]/route.ts`
- `frontend/src/app/approvals/page.tsx`
- `frontend/src/components/controlled-actions.tsx`
- `frontend/src/lib/action-proposals.test.tsx`
- `frontend/src/lib/execution.ts`
- `scripts/aggregate_phase8_eval.py`
- `scripts/prepare_phase8_browser.py`
- `scripts/verify_phase8.py`
