> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 5 — Authorized evidence retrieval and reconciliation

Date: 2026-10-17 (Asia/Kolkata). Baseline: `private-baseline`. Scope: Phase 5 only; no business-changing tools, approvals, deployment or Phase 6.

## 1. What was implemented

Reusable authorized retrieval through the existing ToolExecutor; strict canonical source records; effective-window policy ranking and applicability suggestions; CURRENT/STALE/UNKNOWN freshness with separate historical relevance; deterministic structured conflicts/gaps; grounded finding/citation validation; durable reconciliation; creator/tenant-scoped paginated APIs; source inspection and citation navigation in the workspace; a 28-case measured synthetic retrieval evaluation and reproducible live verifier.

Live verification A–G passed. Evidence: [machine-readable results](assets/phase5-live-verification.json).

| Scenario | Observed result |
| --- | --- |
| A unpaid block | COMPLETED advisory, six calls, 11 sources, matching billing policy |
| B payment conflict | NEEDS_REVIEW, payment_unresolved with source references |
| C security | NEEDS_REVIEW, security_review_required |
| D missing evidence | NEEDS_REVIEW, missing_transaction and missing_block_reason |
| E policy version | Reactivation v2 returned, v1 excluded |
| F foreign tenant | Tool not_found/404, investigation creation 404, no foreign payload |
| G backend restart | Full payment investigation result identical after actual restart; SHA256 recorded |
| H legacy compatibility | Actual pre-Phase 5 completed record readable with six original evidence envelopes |

Health returned `ok`, readiness `ready`, and all three Compose services were healthy. The explicit local verifier adds one fictional missing-evidence customer/account/ticket fixture to the development database; it does not alter seeded account state.

## 2. Files created and modified

Created:

- `backend/alembic/versions/0005_policy_applicability.py`
- `backend/app/schemas/evidence.py`, `backend/app/services/evidence.py`
- `backend/tests/test_evidence.py`, `backend/tests/test_retrieval_evaluation.py`
- `frontend/src/lib/evidence.test.tsx`
- `scripts/verify_phase5.py`
- `docs/architecture/EVIDENCE_RETRIEVAL.md`, `POLICY_SEARCH.md`, `EVIDENCE_RECONCILIATION.md`
- `docs/decisions/0006-evidence-retrieval.md`
- `docs/evaluations/PHASE_5_RETRIEVAL.md`, `phase5-cases.json`, `phase5-results.json`
- This report and `docs/phases/assets/phase5-live-verification.json`

Modified:

- `.env.example`, `AGENTS.md`, `README.md`, `docker-compose.yml`
- `backend/app/agents/contracts.py`, `orchestrator.py`
- `backend/app/api/investigations.py`, `core/config.py`, `db/seed.py`, `models/entities.py`
- `backend/app/services/investigations.py`, `tools/contracts.py`, `tools/handlers.py`
- `backend/tests/test_persistence.py` (both canonical and legacy recovery coverage)
- `frontend/e2e/investigations.spec.ts`, `src/app/api/v1/[...path]/route.ts`, `src/app/globals.css`
- `frontend/src/components/investigation-result.tsx`, `src/lib/investigations.ts`, `vitest.config.ts`
- `docs/architecture/OVERVIEW.md`, `DATA_MODEL.md`

## 3. Architecture decisions

[Decision 0006](../decisions/0006-evidence-retrieval.md) was recorded before implementation. No second authorization/execution system: retrieval wraps ToolExecutor and existing orchestrator scope validation, budgets and checkpoints. Canonical records are additive JSON children of existing tenant-constrained, execution-backed append-only evidence envelopes. Their deterministic IDs, tenant/investigation/execution/time bindings and source references are checked. Terminal reconciliation/finding links are stored in final JSON and deterministically reconstructed for integrity checks. Legacy optional fields preserve old history/checkpoints.

Migration head: **0005_policy_applicability**. Effective dates filter before version precedence; current higher versions suppress lower versions, while future/expired higher versions do not. Keyword key matches precede description matches. Applicability suggestions never authorize actions. Historical ledger records never imply a current balance or reactivation eligibility.

## 4. Commands actually executed

Commands below were executed from the repository root unless a working directory is stated. Synthetic local database credentials are public development defaults; the generated demo password was never printed.

```sh
# Infrastructure/migration/seed
docker compose config --quiet
docker compose up -d db
docker compose build
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.db.seed
docker compose up -d --wait
docker compose exec backend alembic current
docker compose ps
docker compose build backend
docker compose up -d --wait backend

# Static Python checks
backend/.venv/bin/ruff check backend --fix
backend/.venv/bin/ruff check backend scripts/verify_phase5.py
backend/.venv/bin/ruff format --check backend scripts/verify_phase5.py
git diff --check

# backend/ working directory: complete suite + actual metric output
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test \
PHASE5_EVALUATION_OUTPUT=<repository-root> \
.venv/bin/pytest -q

# backend/: additional final canonical/legacy recovery parameterization
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test \
.venv/bin/pytest tests/test_persistence.py::test_safe_recovery_restores_completed_step_without_replay -q

# frontend/ working directory
npm run lint
npm run typecheck
npm test
npm run build

# Authenticated live HTTP checks, including health/readiness and real backend restart
backend/.venv/bin/python scripts/verify_phase5.py --confirm-synthetic-local

# Real browser suite
PLAYWRIGHT_BROWSERS_PATH=/tmp/northstar-browsers \
backend/.venv/bin/python scripts/run_browser_tests.py
```

Intermediate complete runs passed 300 tests before the final recovery/timestamp regression cases. Intermediate checks also ran `pytest -xq` (277 baseline tests), `pytest tests/test_evidence.py tests/test_retrieval_evaluation.py -xq` (16 tests at that point), and a complete 293-test run before the final conflict/security cases were added. The evaluator is part of the complete suite; it uses actual authorized calls, not static expected answers as retrieved output. The live script issued health/readiness requests with httpx and executed `docker compose restart backend`. An additional authenticated one-off httpx/SQLAlchemy check selected an actual owner/tenant-scoped pre-Phase 5 record and verified its API response preserved six legacy evidence envelopes; its proof is included as scenario H.

Exact startup commands for another configured clone:

```sh
# First follow README configuration/password generation instructions.
docker compose up -d db
docker compose build
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.db.seed
docker compose run --rm backend python -m app.db.seed_auth
docker compose up -d --wait
```

The auth seed command above is startup guidance; existing seeded credentials were used for this phase's live checks.

## 5. Test results and failures

- Full final backend run: **302 passed**, one upstream Starlette/httpx deprecation warning, 145.48 seconds. Includes canonical/legacy completed-step recovery and a regression proving creation time is never substituted for source update time.
- Earlier targeted canonical and legacy recovery: **2 passed**, same warning, 3.52 seconds; both are also covered by the final full run.
- Ruff lint/format and diff whitespace checks passed.
- Frontend lint/typecheck passed; **14 Vitest tests** passed in five files.
- Production frontend build passed locally and in Docker.
- **28 Playwright tests passed**, desktop/mobile, 36.0 seconds; source anchors, inspection, freshness, conflict warnings and durable lifecycle verified. Desktop screenshot inspected for layout.
- Compose configuration/build/startup, migration, deterministic/idempotent seed tests and live health/readiness passed.
- Hosted GitHub Actions was not run; its existing test commands discover the new suites.

Measured evaluation (**28 cases**): recall 24/24 = **100%**; precision 24/28 = **85.7143%**; top policy accuracy 17/17 = **100%**; citation validity 28/28 = **100%**; unsupported factual findings **0**; conflict recall **1/1**; tenant leakage **0**. See the [evaluation report](../evaluations/PHASE_5_RETRIEVAL.md) for K, independent labels and scope limits.

Resolved attempts: the first sandboxed database run errored on local TCP access and was interrupted; escalated local runs passed. One policy test initially compared all keyword matches to a single policy version, despite a legitimate billing-description match; the assertion was scoped to the reactivation key, and ranking now prioritizes policy keys. npm commands accidentally run at the monorepo root returned ENOENT and were rerun from `frontend/`. The first live verifier expected a successful HTTP status for a denied tool call; the API correctly returned 404, the assertion was corrected, and all scenarios were rerun successfully. Final review also corrected transaction provenance to retain creation time in metadata and use only an actual last-update timestamp for freshness; absent legacy update times are UNKNOWN. The complete backend and browser suites and live scenarios were rerun successfully afterward. No unresolved test failure remains.

## 6. Security and reliability concerns

No observed tenant leakage, fabricated evidence or unsupported factual finding. Existing server-session/RBAC and investigation ownership checks remain required for every read, dispatch and persistence operation. No request tenant selector, generated SQL, arbitrary HTTP, shell or business-changing tool was added. Prompt/SQL injection tests, strict schema/size checks, source provenance corruption denial, unsupported citations, missing/stale data, duplicate observations, bounded ranking and no-business-mutation checks pass. Existing timeout/cancellation, fail-closed database/tool errors, idempotency, lease fencing and recovery tests remain in the full regression suite. Canonical recovery preserves the original source without another customer tool call.

The local database owner remains privileged; ORM append-only rules and reconstruction are not external tamper-proof storage or PostgreSQL RLS. Source schemas establish provenance, not factual truth. Synchronous tool cleanup can exceed nominal timeout while safely draining, as documented in prior phases. No secrets were added to tracked files. No push or deployment occurred.

## 7. Remaining limitations

Deterministic synthetic acceptance only; no production-readiness claim. Keyword retrieval has no semantic embeddings or synonym handling. Conflict rules cover finite structured cases, not arbitrary source prose or financial reconciliation. One end-to-end conflict metric has a narrow denominator. Freshness is at collection, not a continuous live-state claim; historical relevance and policy effective windows are separate. Old records remain readable with no invented canonical backfill. Applicability is advisory, and final eligibility/approvals/writes remain unimplemented. JSON child references use application validation under the enclosing tenant-aware foreign keys rather than separate source tables. Retention, database RLS and external audit attestation remain future work. Existing development dependency advisories were not expanded into an unrelated dependency-upgrade phase.

## 8. Git status and commit

All Phase 5 source, tests, migration, documentation and measured evidence are included in the local Phase 5 commit. Its exact hash is supplied in the final completion response; embedding a commit's own hash in its contents is not possible. Final working-tree status is checked after commit. No push or deployment.

## 9. Verdict

**PASS** for the requested synthetic Phase 5 scope, supported by the executed checks above. This verdict does not certify production readiness or operational action authority. Phase 6 was not started.
