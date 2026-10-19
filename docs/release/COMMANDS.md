> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Executed final coordinator commands

Run identifier: `20261019T090855157172Z`. All 27 stages below exited zero. The coordinator itself exited one/PARTIAL because rebuilt-image scanning remains blocked. Paths below are normalized relative to each working directory; original argv and durations remain in the local report.

The parent command was:

```sh
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test \
PLAYWRIGHT_BROWSERS_PATH=/tmp/northstar-browsers \
  backend/.venv/bin/python scripts/release_acceptance.py --execute --isolated
```

It loads the ignored local environment, passes mock/development and the isolated DB/origin to isolated steps, and restores the worker. The isolated profile refuses a preexisting release volume. Never remove an unrelated database to rerun it. Do not run individual stages concurrently.

## compose — PASS (0.285 seconds)

```sh
docker compose config --quiet
```

## runtime-mode — PASS (1.302 seconds)

```sh
docker compose exec -T backend python -c 'from app.core.config import get_settings; from sqlalchemy.engine import make_url; s=get_settings(); assert s.ai_provider == '"'"'mock'"'"' and s.app_env in {'"'"'development'"'"','"'"'test'"'"'} and make_url(s.database_url).database == '"'"'northstar'"'"'; print('"'"'Synthetic local backend mode verified'"'"')'
```

## ruff — PASS (0.131 seconds)

```sh
backend/.venv/bin/ruff check --config backend/pyproject.toml backend scripts
```

## format — PASS (0.022 seconds)

```sh
backend/.venv/bin/ruff format --check --config backend/pyproject.toml backend scripts
```

## migrations — PASS (3.812 seconds)

```sh
docker compose run --rm backend alembic check
```

## backend-security — PASS (745.053 seconds)

```sh
(cd backend && .venv/bin/python -m app.evaluations.red_team --regression --output ../artifacts/release/20261019T090855157172Z/security)
```

## lint — PASS (4.949 seconds)

```sh
(cd frontend && npm run lint)
```

## typecheck — PASS (2.113 seconds)

```sh
(cd frontend && npm run typecheck)
```

## test — PASS (1.267 seconds)

```sh
(cd frontend && npm run test)
```

## build — PASS (21.103 seconds)

```sh
(cd frontend && npm run build)
```

## browser-fixtures-operations — PASS (8.209 seconds)

```sh
backend/.venv/bin/python scripts/prepare_phase10_browser.py --confirm-synthetic-local
```

## browser-fixtures-approvals — PASS (3.33 seconds)

```sh
backend/.venv/bin/python scripts/prepare_phase8_browser.py --confirm-synthetic-local
```

## worker-stop-cancellation-tests — PASS (0.407 seconds)

```sh
docker compose stop worker
```

## browser — PASS (76.105 seconds)

```sh
backend/.venv/bin/python scripts/run_browser_tests.py --workers=1
```

## worker-start — PASS (1.022 seconds)

```sh
docker compose up -d worker
```

## release-browser-fixtures — PASS (1.029 seconds)

```sh
backend/.venv/bin/python scripts/prepare_release_browser.py --confirm-synthetic-local
```

## release-browser — PASS (22.048 seconds)

```sh
backend/.venv/bin/python scripts/run_browser_tests.py --config playwright.release.config.ts
```

## performance-smoke — PASS (2.494 seconds)

```sh
backend/.venv/bin/python scripts/release_performance.py --samples 20 --max-p95-ms 250 --concurrency 1 --output artifacts/release/20261019T090855157172Z/performance.json
```

## images — PASS (51.613 seconds)

```sh
docker compose build backend frontend worker
```

## isolated-install — PASS (32.236 seconds)

```sh
backend/.venv/bin/python scripts/release_clean_install.py --confirm-new-synthetic-stack
```

## isolated-release-fixtures — PASS (0.993 seconds)

```sh
backend/.venv/bin/python scripts/prepare_release_browser.py --confirm-synthetic-local
```

## isolated-release-browser — PASS (21.518 seconds)

```sh
backend/.venv/bin/python scripts/run_browser_tests.py --config playwright.release.config.ts
```

## isolated-negative-browser — PASS (44.813 seconds)

```sh
backend/.venv/bin/python scripts/run_browser_tests.py --config playwright.negative.config.ts
```

## isolated-workload — PASS (63.304 seconds)

```sh
backend/.venv/bin/python scripts/release_workload.py --seconds 60 --confirm-synthetic-demo
```

## isolated-persisted-timings — PASS (0.821 seconds)

```sh
backend/.venv/bin/python scripts/release_workload_measurements.py
```

## isolated-queue-load — PASS (26.795 seconds)

```sh
backend/.venv/bin/python scripts/release_queue_load.py --confirm-synthetic-demo
```

## restart-recovery — PASS (26.711 seconds)

```sh
backend/.venv/bin/python scripts/release_recovery.py --confirm-synthetic-local-restarts
```

## Final runtime investigation — local follow-up

Commands actually executed serially (raw stdout, exact argv and durations retained in `artifacts/runtime-review`; public metadata and base-image probes were separate from scans):

```sh
docker compose build frontend
backend/.venv/bin/python scripts/scan_release_images.py
# From backend, with the disposable local TEST_DATABASE_URL configured:
.venv/bin/python -m app.evaluations.red_team --regression --output ../artifacts/runtime-review/backend-security
# From repository root:
backend/.venv/bin/ruff check --config backend/pyproject.toml backend scripts
backend/.venv/bin/ruff format --check --config backend/pyproject.toml backend scripts
docker compose config --quiet
docker compose run --rm backend alembic check
docker build -f infra/docker/frontend.Dockerfile --target build --tag controlled-ai-operations-frontend-checks:phase12 .
docker run --rm --pull never --network none --entrypoint /bin/sh controlled-ai-operations-frontend-checks:phase12 -c 'node --version && npm run lint && npm run typecheck && npm test'
```

The complete image-scan command exited 2 because High findings remain; all three scans completed. Full backend: 727 passed, one upstream warning, 838.59 seconds; 601/601 evaluation scenarios. Frontend: lint/typecheck passed, 50 tests passed. Production build and schema drift checks passed. The first image-binding comparison failed because Docker no longer retained the old running backend/worker image metadata; those services were subsequently recreated from scanned tags before final browser verification. Earlier browser results are kept as a separate pre-binding cohort.

Final image-binding and browser commands (both synthetic stacks' backend/frontend/worker recreated with `--no-build --force-recreate --wait`; DB volumes preserved):

```sh
docker compose up -d --no-build --force-recreate --wait backend frontend worker
docker compose -p northstar-release12 -f docker-compose.yml -f infra/docker/release.compose.yml up -d --no-build --force-recreate --wait backend frontend worker
backend/.venv/bin/python scripts/prepare_phase10_browser.py --confirm-synthetic-local
backend/.venv/bin/python scripts/prepare_phase8_browser.py --confirm-synthetic-local
docker compose stop worker
backend/.venv/bin/python scripts/run_browser_tests.py --workers=1
docker compose up -d worker
backend/.venv/bin/python scripts/prepare_release_browser.py --confirm-synthetic-local
backend/.venv/bin/python scripts/run_browser_tests.py --config playwright.release.config.ts
backend/.venv/bin/python scripts/run_browser_tests.py --config playwright.negative.config.ts
backend/.venv/bin/python scripts/release_recovery.py --confirm-synthetic-local-restarts
```

Browser fixtures/local database URLs and the local Chromium cache were configured by the ignored operator wrapper without printing credentials. Final browser counts: 52 + 4 + 8 passed, no failures/skips/flaky cases, retries disabled. Runtime inventory probes used `docker run --pull never --network none` and local `/proc/1/maps`; no image/SBOM upload. See RUNTIME_VERIFICATION.json for current recovery and live endpoint outcomes.
