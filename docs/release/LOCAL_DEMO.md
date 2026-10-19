> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Reproducible local demonstration

Prerequisites: Docker Compose v2 supporting `!override`, Python 3.12/uv, Node 26.12.0/npm. Run from repository root. All data is fictional. No LLM key is needed.

```sh
cp .env.example .env  # fresh checkout only; preserve an existing ignored configuration
python3 scripts/create_demo_credentials.py
uv sync --project backend --frozen --extra test
npm --prefix frontend ci
docker compose config --quiet
docker compose build backend frontend worker
docker compose up -d db
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.db.seed_auth
docker compose up -d --wait backend frontend worker
curl --fail http://127.0.0.1:8000/api/v1/ready
```

Open http://127.0.0.1:3000/login. Use the identities in README and the generated password in your ignored `.env`; do not display it in a recording. The executor is an operator with `action:execute`, not a fifth database role. Reviewer cannot execute; auditor cannot propose/review/execute. Admin has broader permissions but cannot self-approve or override a security block.

For the full browser journey, prepare existing approval-user and fresh release fixtures:

```sh
backend/.venv/bin/python scripts/prepare_phase8_browser.py --confirm-synthetic-local
backend/.venv/bin/python scripts/prepare_release_browser.py --confirm-synthetic-local
docker compose up -d worker
backend/.venv/bin/python scripts/run_browser_tests.py --config playwright.release.config.ts
```

Fresh fixture records are generated per invocation/project; an already executed release fixture is deliberately not reset. Policies are refreshed by explicit fixture preparation only. Do not run fixture preparation while another suite or recording is using decisions against those policies. For the older cancellation browser cohort stop the worker first; then start it again before the active-worker release cohort. The acceptance runner coordinates this sequence.

## Dedicated database initialization and reset

The ordinary `northstar` database and Compose volume are never deleted by the reset command. Create a separate demo database explicitly:

```sh
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_demo \
  backend/.venv/bin/python scripts/demo_database.py --initialize
```

Initialization refuses an existing database. It migrates/seeds before writing the ownership marker. The credential comes from the ignored `.env`. Stop clients connected to this dedicated database before reset. **The next command deletes all records and history in the marked local demo database:**

```sh
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_demo \
  sh scripts/reset.sh --confirm-synthetic-reset
```

This command refuses `northstar`, remote targets, production mode, nonmock mode, URL query overrides, unmarked databases and live clients. It does not point the existing running application to the new database. Configure a separate instance explicitly if needed. Do not source `.env` as shell code.

An isolated Compose override is supplied at `infra/docker/release.compose.yml`. Always use both files and project `northstar-release12`; its DB/backend/frontend bind 55433/18000/13000. It uses a separate named volume. Initialization of that stack is separate from the database marker tool; do not assume arbitrary populated volumes are resettable.

## Troubleshooting

- Readiness failing: inspect `docker compose ps` and `docker compose logs --tail=100 backend db` locally; do not publish secrets.
- Approval stale: obtain fresh evidence/decision/independent approval; never alter policy/expiry checks to force execution.
- Job uncertain: inspect receipt and reconciliation state; do not submit another mutation key.
- Browser fixture missing: run the appropriate preparer and pass the documented paths. Never silently skip fixture-dependent acceptance checks.
- Existing port busy: stop that instance or choose isolated release ports. Do not delete the primary database volume.
- Runtime images intentionally omit pytest/npm test tooling. Run backend tests in the locked host development environment; the former container `pytest` shortcut is superseded.

## Fresh isolated Compose installation check

After building the runtime images:

```sh
backend/.venv/bin/python scripts/release_clean_install.py --confirm-new-synthetic-stack
```

The check refuses any existing `northstar-release12_northstar_data` volume and confirms Docker access before creating the new stack. It validates Compose, starts an empty DB volume, applies migrations, seeds, starts all services, checks real authentication/readiness/frontend, and checks schema drift. It retains the isolated stack and evidence at `artifacts/clean-install.json`; never automatically deletes an existing volume. A repeated invocation against that volume correctly refuses initialization. Its public URLs are 18000/13000, not the main app's 8000/3000.

For the complete browser journey against this isolated stack, prepare fresh records against its database and use the allowed release origin:

```sh
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55433/northstar_demo \
  backend/.venv/bin/python scripts/prepare_release_browser.py --confirm-synthetic-local
RELEASE_BROWSER_ORIGIN=http://127.0.0.1:13000 \
  backend/.venv/bin/python scripts/run_browser_tests.py --config playwright.release.config.ts
```

The browser helper bypasses earlier lifecycle fixture preparation when the explicit release config is selected. The release suite uses only the selected origin's real HTTP API and fixture IDs. The security-denial scenario uses base tenant-0 seed data in that same stack.

## Isolated negative approval browser cases

With the isolated demo stack running, execute:

```sh
backend/.venv/bin/python scripts/run_browser_tests.py --config playwright.negative.config.ts
```

These eight viewport cases create fresh fictional actors/accounts, obtain real independent approval, then inject exactly one privileged fixture fault: approval expiry, execution-permission revocation, policy-version change or expiry of a real server-side session. Fault preparation refuses the primary database, production/nonmock modes and remote targets. It writes only fixture JSON under ignored repository artifacts. It is a development CLI, never an agent tool or API backdoor. Policy-version changes deliberately invalidate older decisions in the isolated demo; do not run these cases alongside another demo using that same isolated tenant.

The browser checks expired/invalidated or access-denied UI state, hidden execution control, backend denial and unchanged account state/version. The expired-session case checks return to sign-in, two 401 denials and unchanged account data through an independent reviewer session. `RELEASE_DEMO_DATABASE_URL` may override the public synthetic default credential while retaining the strict loopback `northstar_demo:55433` guard. Never put a real credential in source or screenshots. CI is configured to create its own fresh isolated stack for this cohort, but hosted CI has not been run locally.
