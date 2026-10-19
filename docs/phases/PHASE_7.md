> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 7 — deterministic policy eligibility and decision receipts

## 1. Implemented

Evaluation-only PDP with six static actions, strict server-bound proposals, deterministic Python eligibility, exact policy/evidence/resource/permission bindings, five-minute expiry, stale status, append-only revalidation, authenticated CSRF-protected APIs, explicit orchestrator advisory handoff and an Action Proposals workspace. No business execution, approval grants, Phase 8 or paid dependencies.

## 2. Files

- `backend/app/policies/{catalog,engine}.py`, `schemas/actions.py`, `api/actions.py`.
- `backend/alembic/versions/0006_policy_decisions.py`, `models/entities.py`.
- Orchestrator, investigation API, permissions, body limits and FastAPI router integration.
- `backend/tests/test_policy_engine.py`; existing exact authorization expectations extended with the six proposal-only permissions.
- `infra/docker/backend.Dockerfile`: frozen dependency install retained; redundant editable packaging removed.
- Frontend Action Proposals page, proxy allowlist, navigation, Vitest and responsive Playwright checks.
- `scripts/{aggregate_phase7_eval,verify_phase7}.py`, GitHub Actions evaluation artifact.
- AGENTS, README, architecture overview/authorization, three policy architecture documents, decision 0008, evaluation/report and generated verification artifacts.

## 3. Architecture decisions

See [0008](../decisions/0008-policy-decisions.md). The PDP composes live existing authorization and canonical investigation evidence, independently resolving current structured policies. It neither expands ToolRegistry nor executes tool writes. Effective policy windows must resolve unambiguously: overlapping active versions deny. Search rank and policy prose cannot grant permission. Revalidation appends receipts and retains prior decisions. Proposal locks and unique sequence constraints serialize concurrent requests.

Migration head: `0006_policy_decisions` (from `0005_policy_applicability`). ALLOW means eligibility, not completed execution or durable authorization.

## 4. Commands executed

Commands actually executed (from repository root unless noted):

```sh
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test \
  PHASE7_EVALUATION_DIR=/tmp/northstar-phase7-evaluation \
  backend/.venv/bin/pytest -c backend/pyproject.toml backend/tests -xq
backend/.venv/bin/ruff check --config backend/pyproject.toml backend scripts
backend/.venv/bin/ruff format --config backend/pyproject.toml --check backend scripts
```

From frontend: `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`.

```sh
docker compose config --quiet
docker compose run --rm backend alembic current
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar \
  backend/.venv/bin/python scripts/verify_phase7.py --confirm-synthetic-local
PLAYWRIGHT_BROWSERS_PATH=/tmp/northstar-browsers \
  backend/.venv/bin/python scripts/run_browser_tests.py --workers=1
backend/.venv/bin/python scripts/aggregate_phase7_eval.py --input /tmp/northstar-phase7-evaluation
git diff --check
```

Targeted Phase 7 pytest runs preceded the complete regressions; resolved failed attempts are documented below. Both image builds were actually run, including the successful backend rebuild after the packaging timeout.

Exact startup:

```sh
docker compose up -d db
docker compose build backend frontend
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.db.seed_auth
docker compose up -d backend frontend
```

Existing ignored local environment and demo credential are required; a fresh checkout first follows README configuration. Both the base `python -m app.db.seed` and authentication seed commands were executed, preserving existing credentials. No credential values were logged.

## 5. Results and failures

Final backend pytest: **425 passed**, one upstream deprecation warning, **243.98 seconds**. This includes all prior regressions and 61 Phase 7 tests. Completed checks:

- Policy evaluation: accuracy 41/41; unsafe ALLOW 0/39; unsafe REQUIRE_APPROVAL 0/38; false denial 0/5; stale rejection 10/10; foreign-target binding leakage 0/2, plus hidden cross-tenant proposal retrieval.
- Frontend lint/typecheck and local production build passed; Vitest 20/20.
- Final-image Playwright: 30/30 passed in 38.5 seconds (desktop and mobile). The UI also labels expired receipts STALE locally; backend checks remain authoritative.
- Ruff and formatting passed (77 Python files); diff whitespace check passed.
- Compose configuration, final image builds, migration head 0006, deterministic seed verification and health/readiness passed. All three services healthy.
- Live A–G: customer note ALLOW; reactivation REQUIRE_APPROVAL; security override DENY; conflicting evidence DENY; resource change STALE and revalidation DENY; foreign target DENY; superseding policy change STALE.
- Evaluation business mutations: 0, using full business-table snapshots. Explicit synthetic verifier fixtures restored exactly.
- Existing Starlette/httpx upstream deprecation warning remains; no failed final check is accepted.

Resolved development failures: fixture used the wrong Limits field name; ticket-note fixtures initially cited unrelated tickets; one closed-ticket fixture changed a different ticket; HTTP strict UUID and nested response decoding required explicit JSON-boundary validation. Existing exact navigation/permission tests required authorized proposal additions. Initial Ruff format check identified the updated permission test formatting. The first Docker backend image attempt timed out retrieving isolated setuptools build requirements; the redundant editable install was removed, while frozen dependency installation remained, and the rebuilt image passed live checks. One file edit was attempted from frontend cwd and failed without changing a file; corrected from repository root. The strict numeric-policy fixture initially did not persist its change because ORM JSON equality treats 1 and True as equal; explicit dirty tracking and a readback now verify the malformed persisted value before asserting DENY. All failures were fixed without weakening authorization, receipt validation or runtime bounds.

## 6. Security and reliability

No execution permission, approval grant or execution endpoint exists. Unknown actions, unsupported policy shapes, missing evidence, stale facts, security overrides and conflicting active policies deny. Foreign targets do not expose foreign bindings; proposal retrieval hides foreign IDs. Business equality is checked across evaluation calls. Immutable history remains application-level ORM enforcement, not protection against privileged SQL.

## 7. Limitations

Synthetic mock evaluation does not establish production readiness. Explicit limited rule shapes support the seeded scenario; policy administration and arbitrary rule languages are absent. Notes have bounded conservative content validation, not comprehensive secret detection. Fixed-date seed evidence becomes stale honestly; the local verifier explicitly prepares and restores fresh synthetic fixtures. Revalidation of changed evidence usually requires a new investigation before eligibility can return. No approval/execution, external enterprise integrations, RLS, cryptographic audit storage or hosted deployment. Hosted GitHub Actions were configured but not run; no paid LLM calls were made.

## 8. Git

Successful verification completed before the local Phase 7 commit. The final response records the commit hash; `git log -1 --format=%H` retrieves it. No push or external deployment.

## 9. Verdict

**PASS** for the evaluation-only Phase 7 scope. No unauthorized ALLOW/REQUIRE_APPROVAL, foreign binding leakage or evaluation business mutation was observed in the tested cases. Phase 8 was not started.

## Complete changed paths

- `.github/workflows/ci.yml`
- `AGENTS.md`
- `README.md`
- `backend/alembic/versions/0006_policy_decisions.py`
- `backend/app/agents/orchestrator.py`
- `backend/app/api/actions.py`
- `backend/app/api/investigations.py`
- `backend/app/core/permissions.py`
- `backend/app/core/tool_body_limit.py`
- `backend/app/main.py`
- `backend/app/models/entities.py`
- `backend/app/policies/catalog.py`
- `backend/app/policies/engine.py`
- `backend/app/schemas/actions.py`
- `backend/tests/test_authentication.py`
- `backend/tests/test_policy_engine.py`
- `docs/architecture/ACTION_CATALOG.md`
- `docs/architecture/AUTHORIZATION.md`
- `docs/architecture/DECISION_RECEIPTS.md`
- `docs/architecture/OVERVIEW.md`
- `docs/architecture/POLICY_ENGINE.md`
- `docs/decisions/0008-policy-decisions.md`
- `docs/evaluations/PHASE_7_POLICY_EVAL.md`
- `docs/evaluations/phase7-results.json`
- `docs/phases/PHASE_7.md`
- `docs/phases/assets/phase7-live-verification.json`
- `frontend/e2e/shell.spec.ts`
- `frontend/src/app/action-proposals/page.tsx`
- `frontend/src/app/api/v1/[...path]/route.ts`
- `frontend/src/lib/action-proposals.test.tsx`
- `frontend/src/lib/action-status.ts`
- `frontend/src/lib/navigation.test.ts`
- `frontend/src/lib/navigation.ts`
- `infra/docker/backend.Dockerfile`
- `scripts/aggregate_phase7_eval.py`
- `scripts/verify_phase7.py`
