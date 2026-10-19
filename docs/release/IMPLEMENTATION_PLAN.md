> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 12 repository audit and priority plan

Baseline: private-baseline. Scope is synthetic local verification only.

1. **P0 acceptance evidence:** retain every failed check, execute serially, do not infer release acceptance from Phase 11 results. Existing 48 browser cases cover individual controls but no single investigation → proposal → independent review → durable worker → receipt → auditor journey. Add an active-worker suite with fresh records and no HTTP mocks.
2. **P1 reset safety:** the existing reset script calls `docker compose down --volumes` without target validation. Replace with dedicated loopback `northstar_demo` tooling, an ownership marker, explicit initialization/reset modes and live-client refusal. Preserve the ordinary development database and volume.
3. **P1 repeatability:** add a serial acceptance entrypoint with exact argv, duration, exit status, logs and explicit missing-evidence list. Existing frontend cancellation case requires stopped worker; isolate that cohort from active-worker journeys.
4. **P2 measurement:** collect bounded read-only API samples at configurable 1–20 concurrency. Report errors and sample counts, omit unsupported p99; do not infer write throughput, fairness or sustained workflow reliability.
5. **P2 release review:** record dependency scanner availability/results, image privilege/configuration review, trusted-Origin CSRF assumptions, production configuration gaps and historical instability. No speculative indexes or major dependency updates.
6. **P2 additional verification:** clean install, bounded workflow load/soak, restart/recovery, query plans and repeat full suites require their own fresh evidence. Keep the release verdict PARTIAL until these requirements and all negative browser workflows are established.

Inspection covered startup/settings, route families/authentication, seven existing browser files, fixture scripts, Compose, PostgreSQL worker leases/caps, migrations, seeds, environment template, CI, locks, logs/metrics, readiness and the Phase 11 source-bound evaluator. No new framework or broker is needed. Existing query and trace bounds should be measured before tuning. ORM immutability does not protect against the database owner. Current frontend runtime image includes development dependencies; scanner findings must distinguish installation from execution reachability.
