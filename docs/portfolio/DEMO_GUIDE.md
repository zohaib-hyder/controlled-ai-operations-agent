# Reproducible synthetic local demonstration

Use mock AI, loopback ports and fictional data. This demonstration exercises implemented functionality; it does not clear Phase 12's PARTIAL release gate.

## Configure, build and seed

Follow the [README startup commands](../../README.md#local-setup). The public DB password placeholder is disposable and local-only. `scripts/create_demo_credentials.py` creates a random operator/reviewer fixture password in ignored `.env`, chmod 0600, without printing it. Never put credentials in screenshots, browser recordings or source. Ordinary seed data is deterministic/idempotent; generated demo credentials are deliberately not deterministic.

The default publication Compose project uses a separate volume from the private original. Both default stacks still bind 3000/8000/55432; do not run both on those ports. The preparation verification uses an ignored override and its own ports/database. Never point these tools at a customer system.

| Tenant | Executor | Independent reviewer | Auditor |
| --- | --- | --- | --- |
| Atlas | operator.0@example.com | reviewer.0@example.com | auditor.0@example.com |
| Beacon | operator.1@example.com | reviewer.1@example.com | auditor.1@example.com |

Admin fixtures use `admin.0@example.com` and `admin.1@example.com`. All are fictional; passwords come only from your ignored configuration. Use separate browser contexts for actors. Seeding preserves existing hashes; changing `.env` does not reset previously provisioned accounts.

## Fresh workflow fixtures

From repository root with the seeded stack running and backend development dependencies installed:

```sh
backend/.venv/bin/python scripts/prepare_release_browser.py --confirm-synthetic-local
```

This guarded local fixture CLI prepares fresh synthetic release records. Use the current fixture identifiers produced/stored by the script; do not reuse a committed proposal or approval. The browser journey source is [workflow.spec.ts](../../frontend/release-e2e/workflow.spec.ts).

## Investigation and evidence

1. Sign in as `operator.0@example.com`, open Investigations and choose the fresh fictional customer/account with resolved billing.
2. Ask for a read-only account-reactivation investigation. Inspect bounded steps, actual tool results, canonical citations, freshness and reconciliation. Ticket prose is untrusted evidence.
3. Inspect policy matches and conflicting/gap evidence. Compare a security-review or unpaid-billing scenario; do not imply every case is eligible.

## Policy, approval and controlled execution

1. Open Action proposals. Use the actual investigation/account and canonical evidence IDs, choose `reactivate_account`, and evaluate the deterministic decision.
2. For REQUIRE_APPROVAL, request approval. The original executor cannot independently approve its own request.
3. In a separate context, sign in as `reviewer.0@example.com`. Inspect the exact request/evidence/versions, enter a reason and approve. A separate fresh case can show rejection.
4. Return to the original executor. Submit the exact proposal/decision/approval in Execution jobs. Let the actual worker process it.
5. Inspect completed status and the verified COMMITTED receipt, before/after account version, audit and correlation timeline. Replay the same submission key to demonstrate the same durable job/receipt. Do not switch keys to force duplicate work.
6. As auditor, inspect Diagnostics and the actual correlation graph; no mutation controls should be available.

See the [detailed historical demo script](../release/DEMO_SCRIPT.md). The model cannot authorize execution; approval does not remove immediate revalidation.

## Operations and recovery

Open Operations Command Center and filter the tenant/time range. Inspect real job status, backlog, workers and any actual fixture incident. Acknowledge/resolve operational metadata only with a permitted actor; this never repairs business state or authorizes retry.

The guarded recovery check restarts this local Compose stack and queues a synthetic note. Run it only against its supported primary loopback development configuration, serially, with no other demonstration active:

```sh
backend/.venv/bin/python scripts/release_recovery.py --confirm-synthetic-local-restarts
```

It checks preserved durable snapshot, queued completion, same-key replay, one receipt and one business record. Read its actual report; a graceful queued restart is not crash-at-commit or external failover evidence. Never delete a volume just to show recovery.

## Evaluation CLI and browser verification

Create a disposable `northstar_test` DB, install locked dependencies, and from backend run:

```sh
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test \
  .venv/bin/python -m app.evaluations.red_team --regression --output ../artifacts/security
```

This is destructive to a marked test DB and refuses an ordinary application database. Run alone. Source-bound results, failures and gaps are local artifacts. Standard checks require mock mode and block real HTTP transports.

For the complete browser workflow, install locked Chromium, prepare fresh release fixtures, and from repository root run:

```sh
backend/.venv/bin/python scripts/run_browser_tests.py --config playwright.release.config.ts
```

Default browser regression also needs operations/approval fixtures and controlled worker stop/restore for cancellation checks; follow [release commands](../release/COMMANDS.md). Do not present an unrun command as passed.

## Recording and shutdown

Only capture actual screens with synthetic records. Avoid login fields, `.env`, terminal history, browser storage and network panels. Required views and actual capture status are in [SCREENSHOTS](SCREENSHOTS.md). End with the limitations/security panel and disclose PARTIAL. Stop with `docker compose down`; do not add `-v` to remove data.
