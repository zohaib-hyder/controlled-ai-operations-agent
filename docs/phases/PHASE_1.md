> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 1 — Authentication, Multi-Tenancy and RBAC

Date: 2026-10-16 (Asia/Kolkata). Base commit: `private-baseline`. Scope excludes the agent, tool registry, approval workflow, business mutations and Phase 2.

## 1. What was implemented

- Argon2id email/password login, opaque random sessions stored only as SHA-256 token digests, fixed expiry, logout revocation and browser-session rotation on successful login. Current identity is resolved server-side on every request, including current user activity and role.
- Host-only HttpOnly/SameSite=Lax cookies with explicit expiry/path. Production validation requires Secure cookies and HTTPS origins, rejects demo passwords, and hides secret inputs in configuration validation errors.
- Exact Origin/Fetch Metadata validation on auth POSTs. No browser token storage, broad CORS, JWT claims or third-party identity provider.
- Persistent PostgreSQL login-failure protection: per-email and backend-observed client buckets with transaction advisory locks. Generic authentication errors, standard API errors and no-store responses.
- Central operator/reviewer/admin/auditor permission matrix and reusable permission dependencies. Read-only tenant-scoped customer/account/ticket list/detail APIs, UUID validation, bounded pagination and identical foreign/nonexistent resource 404s. Session/role/tenant never come from client selectors.
- Login/failure/logout/revocation/permission-denial/resource-access-denial security events with correlation IDs and append-only application behavior.
- Additive migration `0002_authentication`, preserving business data and existing user IDs, converting legacy approvers to reviewers. Nullable credentials leave pre-existing users unable to authenticate until provisioned. Global normalized email uniqueness supports email-only login.
- Explicit development-only auth seed: two admins added while preserving all six original users, yielding **eight demo identities**, four roles per tenant. Base business counts remain 2 tenants, 20 customers, 20 accounts, 30 tickets, 40 transactions and 10 policy versions. Random-salted hashes are preserved across repeated seeding. No demo login passwords are committed.
- Same-origin Next.js API proxy, login, authenticated shell, role/user display, permission-aware navigation, logout, loading/error/unauthorized/session-invalid states, customer list/detail, account list and ticket list. The enterprise design and honest later-phase placeholders are preserved.
- Updated CI to use a real API and disposable PostgreSQL for authenticated browser checks; ephemeral credentials are generated into the runner environment without printing them. Hosted CI was not run.

## 2. Files created and modified

### Created

- `backend/alembic/versions/0002_authentication.py`
- `backend/app/api/auth.py`
- `backend/app/api/business.py`
- `backend/app/core/passwords.py`
- `backend/app/core/permissions.py`
- `backend/app/db/seed_auth.py`
- `backend/app/schemas/auth.py`
- `backend/app/schemas/business.py`
- `backend/app/services/authentication.py`
- `backend/app/services/repository.py`
- `backend/app/services/security_audit.py`
- `backend/tests/test_authentication.py`
- `docs/architecture/AUTHENTICATION.md`
- `docs/architecture/AUTHORIZATION.md`
- `docs/architecture/TENANT_ISOLATION.md`
- `docs/decisions/0002-authentication.md`
- `docs/phases/PHASE_1.md`
- `docs/phases/assets/phase-1-customers-desktop.png`
- `docs/phases/assets/phase-1-customers-mobile.png`
- `docs/phases/assets/phase-1-login-desktop.png`
- `frontend/src/app/accounts/page.tsx`
- `frontend/src/app/api/v1/[...path]/route.ts`
- `frontend/src/app/customers/[id]/page.tsx`
- `frontend/src/app/login/page.tsx`
- `frontend/src/app/tickets/page.tsx`
- `frontend/src/components/auth-provider.tsx`
- `frontend/src/components/resource-list.tsx`
- `frontend/src/components/shell.tsx`
- `frontend/src/lib/api.test.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/types/auth.ts`
- `scripts/create_demo_credentials.py`
- `scripts/run_browser_tests.py`

### Modified

- `.env.example`
- `.github/workflows/ci.yml`
- `AGENTS.md`
- `README.md`
- `backend/alembic/env.py`
- `backend/alembic/versions/5cdee4cd2488_initial_synthetic_enterprise_schema.py`
- `backend/app/core/config.py`
- `backend/app/db/seed.py`
- `backend/app/main.py`
- `backend/app/models/entities.py`
- `backend/pyproject.toml`
- `backend/tests/conftest.py`
- `backend/tests/test_system.py`
- `backend/uv.lock`
- `docker-compose.yml`
- `docs/architecture/DATA_MODEL.md`
- `docs/architecture/OVERVIEW.md`
- `frontend/e2e/shell.spec.ts`
- `frontend/src/app/approvals/page.tsx`
- `frontend/src/app/audit/page.tsx`
- `frontend/src/app/customers/page.tsx`
- `frontend/src/app/globals.css`
- `frontend/src/app/investigations/page.tsx`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/page.tsx`
- `frontend/src/app/settings/page.tsx`
- `frontend/src/components/sidebar.tsx`
- `frontend/src/lib/navigation.test.ts`
- `frontend/src/lib/navigation.ts`

Historical migration `5cdee4cd2488` has import-group whitespace normalization only; its schema operations are unchanged. Foundation regression tests retain behavior checks, with the public-data-route expectation intentionally updated from absent (404) to authentication-required (401) now that those routes exist. Other small test import changes reflect the locked Ruff configuration.

## 3. Architecture decisions

See [repository audit/decision 0002](../decisions/0002-authentication.md), [authentication](../architecture/AUTHENTICATION.md), [authorization](../architecture/AUTHORIZATION.md), [tenant isolation](../architecture/TENANT_ISOLATION.md) and the updated overview/data model.

- Prefer opaque server sessions to client authorization claims. Store only token digests; bind sessions to tenant/user with a composite FK and re-evaluate current roles on requests.
- Use globally unique `lower(email)` for unambiguous email-only login. A duplicate normalized email makes the migration fail transactionally rather than merge tenant identities.
- Preserve existing composite business FKs. Build HTTP queries through an identity-bound repository, including scoped counts. Do not perform unscoped existence probes to classify 404s; log the same resource-access-denied event for missing/foreign IDs.
- **RLS evaluated and deferred.** The foundation uses a DB-owner connection. Policies on that bypass-capable connection would be misleading without separate runtime-role provisioning, grants, transaction-local context and pool-leak tests. Explicit repository constraints are authoritative in this phase; privileged DB access remains outside that boundary. No RLS tests are claimed.
- Require exact Origin validation for login/logout and same-origin proxying. Local HTTP uses explicit development cookies; production rejects insecure transport configuration.
- Keep the requested non-read permission names as reserved contracts. No business/user-role mutation or approval endpoint is added. Auditor business access is read-only, as is all business access in this phase.
- Security events are append-only through application behavior/ORM hooks, not a cryptographically immutable or privilege-proof database ledger. Automatic auth migration downgrade refuses to discard security records.

## 4. Commands actually executed

Repository audit included reading the attached request, AGENTS.md, actual model/session/settings/seed/API files, the existing migration, tests, frontend layout/navigation, Compose and CI; `git status --short` confirmed a clean starting tree.

Meaningful implementation/verification commands (from repository root unless `cd` is shown):

```sh
UV_CACHE_DIR=/tmp/northstar-uv uv sync --project backend --python 3.12 --extra test
UV_CACHE_DIR=/tmp/northstar-uv uv sync --project backend --extra test
cd backend
.venv/bin/alembic upgrade head
.venv/bin/python -m app.db.seed_auth
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test .venv/bin/pytest -q
cd ..
python3 scripts/create_demo_credentials.py
backend/.venv/bin/ruff check --config backend/pyproject.toml backend scripts --fix
backend/.venv/bin/ruff format --config backend/pyproject.toml backend scripts
backend/.venv/bin/ruff check --config backend/pyproject.toml backend scripts
npm run lint --prefix frontend
npm run typecheck --prefix frontend
npm test --prefix frontend
npm run build --prefix frontend
docker compose config --quiet
docker compose build
docker compose build backend
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.db.seed_auth
docker compose up -d --wait
docker compose up -d --wait backend
docker compose run --rm -e TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@db:5432/northstar_test backend pytest -q -o cache_dir=/tmp/northstar-pytest-cache
PLAYWRIGHT_BROWSERS_PATH=/tmp/northstar-browsers backend/.venv/bin/python scripts/run_browser_tests.py
backend/.venv/bin/python /tmp/northstar_phase1_live.py
docker compose ps
docker compose exec -T backend alembic current
npm audit --prefix frontend --omit=dev --cache /tmp/northstar-npm
npm audit --prefix frontend --json --cache /tmp/northstar-npm
git diff --check
git add .
git diff --cached --check
git diff --cached --stat
git commit -m "feat: add tenant-scoped sessions and role-based access control"
git status --short
git rev-parse HEAD
git check-ignore .env backend/.venv frontend/node_modules frontend/.next
```

Source files were generated/edited locally and formatted with Ruff and Prettier. Temporary Playwright screenshot code captured login and synthetic customer views without credentials displayed. A local check executed the CI credential-generation Python snippet against a temporary file, verifying one newline-terminated environment record without printing its value. Dependency downloads were retried with elevated network access after sandbox restrictions; no security checks were disabled. A staged-file scan confirmed the actual ignored local demo password did not occur in any staged file. Final Compose status showed all three services healthy and `alembic current` reported `0002_authentication (head)`.

Exact fresh-checkout startup:

```sh
cp .env.example .env
python3 scripts/create_demo_credentials.py
docker compose config --quiet
docker compose build
docker compose up -d db
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.db.seed_auth
docker compose up -d --wait
```

For the existing Phase 0 working copy, preserve `.env` and the database volume, add settings from `.env.example`, then build/upgrade/seed as above. Login at http://localhost:3000/login using a fictional address from README and the password in ignored `.env`. Do not source that JSON-bearing file as a shell script. No credential values are included in this report.

## 5. Test results and failures

- Local PostgreSQL pytest: **75 passed**. This includes the 21 Phase 0 regression checks plus authentication, cookie/CSRF, throttling, exact RBAC, both directions of customer/account/ticket isolation, spoofed selectors, role revalidation, audit behavior, session persistence, auth-seed safeguards and migration-upgrade tests.
- Containerized pytest: **75 passed**, with the same upstream TestClient adapter warning.
- Ruff: passed. Frontend ESLint: passed. TypeScript: passed. Vitest: **7 passed** across two files. Next.js production webpack build: passed, including the fixed-route proxy and customer detail route.
- Playwright: **10 passed**, five scenarios at each desktop/mobile viewport: real login/tenant data/navigation/logout, direct unauthorized-page handling, revoked-token stale UI, generic invalid credentials and browser cookie expiry. Backend tests separately exercise server-side expiry.
- Compose validation/build: passed. Migration and explicit auth seed commands succeeded in Docker. Live HTTP checks verified process/database status, unauthenticated rejection, hostile-Origin rejection, valid login, scoped counts 10/10/15, foreign UUID denials for all three resources and logout denial afterward.
- Login and customer screenshots were visually reviewed. CI credential-generation snippet checked locally; hosted GitHub Actions was not run.
- Runtime npm audit: **0 vulnerabilities**. Full audit retains the Phase 0 development-tool findings: **5 high-severity findings**, in `eslint-config-next → @next/eslint-plugin-next → fast-glob → micromatch → braces` (GHSA-vfj7-8cjw-p6xm). The full audit exits 1; no forced downgrade or security-check suppression was applied.

Resolved failures: initial Ruff import/style issues and React effect-state lint errors were corrected without suppression. One container test incorrectly inherited the development demo password into its expected-success production settings case; the positive test now explicitly supplies no demo password while the forbidden-demo and insecure-cookie assertions remain enforced. Configuration errors additionally hide input values. Two initial browser failures matched both the real form error and Next.js's empty route-announcer alert; the locator now scopes to the form and still asserts the exact generic message. The corrected browser run passed all ten cases. No critical auth or isolation failure remains in the passing local suite.

Warnings: upstream Starlette warns about the httpx TestClient adapter; Playwright emits a NO_COLOR/FORCE_COLOR environment warning. Neither is represented as a production certification or silently suppressed.

## 6. Security and reliability concerns

RLS/database least privilege are deliberately not implemented. The runtime connection remains privileged; a repository bypass or direct DB access can cross tenant boundaries. Append-only ORM guards do not prevent privileged raw SQL/bulk mutation of audit records. The existing full npm audit findings affect lint dependencies also present in these development/foundation container images; runtime-only audit is clean. Local HTTP cookies are intentionally not transport-secure and are prohibited by production settings.

The proxy shares its observed backend address across clients, so its 30-failure throttle can temporarily affect the whole demo workspace. Production edge abuse control and concurrency/load testing remain future work. Expired sessions and security events have no automated retention worker. No login passwords/raw session tokens are stored in audit events, logs or Git; `.env` is ignored and generated with restrictive permissions. Shared fixture credentials are explicitly development-only.

## 7. Remaining limitations

No agent, tool registry, approval workflow, business mutations, real provider, user/role-management interface, MFA, password recovery/change or global device-management UI. Reserved permissions do not imply those features work. No RLS, production TLS end-to-end test, production-load assessment, penetration test or hosted CI run. Automatic downgrade is intentionally refused; use a reviewed restore/migration plan. Authentication hash salts are random by design; structural fixture IDs and repeat-seed behavior are deterministic. No production-readiness claim is made.

## 8. Git status and commit

This report belongs to the requested local Phase 1 commit after successful verification. The final response records the observed commit hash and working-tree status; `git log -1` retrieves the hash without embedding a self-referential commit ID in this file. `.env`, dependencies, build outputs, caches and test results are ignored. No GitHub push, external deployment or Phase 2 work was performed.

## 9. Verdict

**PASS — Phase 1 scope.** All final authentication, authorization and tenant-isolation checks pass. RLS is explicitly deferred under the permitted tradeoff; development-tool audit findings and production limitations remain disclosed. This is not a production-readiness claim.
