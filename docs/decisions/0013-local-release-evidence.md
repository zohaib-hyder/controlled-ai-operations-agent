# 0013 — Local release evidence and dedicated demo reset

Status: accepted implementation approach; release acceptance remains conditional on verification.

Use existing real API/PostgreSQL/worker services for browser release verification. Keep old cancellation tests in a stopped-worker cohort and independent approval/durable execution in an active-worker cohort. Generate fresh per-project fictional records rather than reset approved/mutated resources shared with another test. Use semantic selectors, response events and bounded polling; do not introduce retries or mock the primary journey.

Coordinate heavy checks serially in a development-only Python CLI. Persist exact argv, durations, status and artifacts after each stage. An absent check or incomplete required evidence cannot establish acceptance. Run subprocesses in separate process groups and terminate descendants on timeout. This harness is not an agent tool and never grants authority.

Replace volume-wide reset with exact-target local demo initialization and explicit reset. Initialization refuses existing databases; reset requires a synthetic ownership marker and no connected clients. A marker is an accidental-destruction guard under a trusted local DB owner, not an authorization boundary against that owner. Deleted history cannot be restored by migration downgrade.

Use multi-stage images to separate locked dependency/build tooling from nonroot runtime images. Backend excludes pytest/Ruff/uv/pip; frontend copies Next standalone output rather than the entire build toolchain. Retain the same business services and schema. No migration, broker or agent framework is introduced.

Do not tune indexes or service budgets without evidence. Read-only HTTP timings, representative small-data query plans and queued-job restarts each support only their stated scope. Production capacity, strict fairness, full failure-mode coverage and live-provider safety need independent evidence.

A measured 20-client cohort exposed pool starvation: the HTTP identity dependency retained one connection while service handlers acquired another from the same finite pool. Use a separate short-lived authentication Session bound to the injected database; close it before returning immutable identity fields. Keep all session/role/tenant predicates and service write revalidation. A real single-connection-pool regression test checks release on both successful and revoked-session paths. No pool timeout/capacity or agent budget is raised. The repeated load cohort is recorded separately; this diagnosis is not asserted to explain the historical Phase 10 transient.
