> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Local performance baseline

Run only against the local synthetic API; mock provider is required. The harness uses a fixed loopback URL, disables environment proxy forwarding and performs bounded authenticated reads. It logs no credentials or bodies.

```sh
backend/.venv/bin/python scripts/release_performance.py --samples 20 --concurrency 1 --output artifacts/performance-c1.json
backend/.venv/bin/python scripts/release_performance.py --samples 20 --concurrency 5 --output artifacts/performance-c5.json
backend/.venv/bin/python scripts/release_performance.py --samples 20 --concurrency 10 --output artifacts/performance-c10.json
backend/.venv/bin/python scripts/release_performance.py --samples 20 --concurrency 20 --output artifacts/performance-c20.json
backend/.venv/bin/python scripts/release_query_plans.py
```

Reports include request/success/error counts, p50/p95, p99 only for 100+ samples, throughput, duration, concurrency, Python/platform/CPU count. Latency includes errors, if observed. Login is one sample and is reported separately; no meaningful tail distribution can be established from it. No samples are fabricated or dropped as warmup. Operations rate limits may reject repeated high-frequency cohorts; such responses must remain errors in the report.

These are local read-path baselines, not a sustained mixed-workflow soak, worker fairness benchmark or production capacity test. Investigation creation, per-tool and retrieval execution, PDP/approval creation, submission, queue wait and controlled execution latency require separate workflow measurement. Define performance targets only after observing valid local measurements; no unmeasured service-level objective is asserted.

Query diagnostics use fixed, tenant-bound SELECT shapes with read-only transactions and three-second statement timeouts. They do not reproduce every ORM query or production cardinality. Small synthetic tables may appropriately use sequential scans. Add no index without a measured growing-table bottleneck and migration justification. Existing API pagination/graph limits remain unchanged.

## Bounded mixed workflow workload

After the isolated clean-install stack is running, execute:

```sh
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55433/northstar_demo \
  backend/.venv/bin/python scripts/release_workload.py --seconds 60 --confirm-synthetic-demo
```

The harness refuses the main database/port, nonlocal targets, nonmock mode and durations outside 30–120 seconds. It creates fresh fictional records in the isolated DB and alternates tenants with serial, paced eight-second arrivals with fresh synthetic operator accounts. It measures actual API operations for investigations, PDP, approval creation/review, job submission/completion, replay, receipt verification, metrics and incident detection. It checks one receipt/record per committed proposal and foreign-tenant job denial. Counts, errors, observed backlog and latency samples remain in `artifacts/workload.json`. A shorter completed workflow count is not extrapolated to saturation throughput. Failed iterations fail the harness; no retry hides a failure.

This exercises mixed approval requirements, not a mixed accepted/rejected job cohort or moderate concurrent queue. Serial completion does not establish global admission-cap fairness; initial/final process monitoring and real fault recovery require separate evidence. No unexpected-exit claim is inferred from HTTP success alone.

## First observed baseline

Fresh concurrency-one cohort: 20 samples per read endpoint, all 160 succeeded. Host: macOS 26.3.1 arm64, Python 3.12.14, eight logical CPUs. Authentication had one successful 281.18 ms observation; it is not a tail distribution. Read p99 is omitted because each endpoint has fewer than 100 samples.

| Endpoint | n | p50 ms | p95 ms |
| --- | ---: | ---: | ---: |
| health | 20 | 2.31 | 3.13 |
| ready | 20 | 3.34 | 3.69 |
| customers | 20 | 5.92 | 6.81 |
| investigation_history | 20 | 15.13 | 56.62 |
| approval_queue | 20 | 9.30 | 13.52 |
| execution_jobs | 20 | 8.83 | 10.18 |
| operations | 20 | 39.76 | 67.24 |
| incidents | 20 | 11.73 | 25.05 |

These results are an initial local baseline, not evidence of an improvement. A prospective repeat-cohort smoke target of zero read errors and p95 below 250 ms at concurrency one is proposed from the observed maximum 67.24 ms. It is a local regression alarm with headroom, not a production SLA or an already-proven repeat guarantee. Higher concurrency requires its own measured targets.

## Bounded load and observed remediation

All cohorts used 20 reads per endpoint (160 reads per cohort), fixed loopback URL and one authenticated synthetic administrator. p99 is not reported for these sample sizes. The following table reports the slowest endpoint p95, not a pooled request percentile.

| Configured clients | Successful reads | Errors | Slowest endpoint p95 ms |
| --- | ---: | ---: | ---: |
| 1 | 160/160 | 0 | 67.24 |
| 5 | 160/160 | 0 | 318.99 |
| 10 | 160/160 | 0 | 591.67 |
| 20 before | 91/160 | 69 | 3267.66 |
| 20 after | 160/160 | 0 | 687.30 |

The initial 20-client cohort exposed three-second connection-pool starvation in authenticated service routes. The HTTP authentication dependency retained a connection while handlers requested another from the same pool. A short-lived authentication Session now closes before returning immutable identity data; all identity predicates and immediate write revalidation remain unchanged. The real one-connection regression test and 67 focused authentication/release tests passed. The exact 20-client cohort then passed 160/160 reads without changing pool size, pool timeout, statement timeout or agent budgets. This is evidence for that bottleneck and remediation; it does not establish the historical Phase 10 failure cause.

A prospective local 20-client repeat target of zero errors and per-endpoint p95 below 1500 ms is grounded in the observed post-fix maximum of 687.3 ms. It remains a local regression alarm, not a production SLA or saturation limit. The failing cohort is preserved; its errors are not dropped from the results. No authentication percentile distribution is inferred from each cohort's single login.

## Observed paced workflow measurements

The first isolated 60.003-second mixed workload completed eight workflows (four per tenant), four independent grants and zero failed workflows/duplicate mutations. Eight sampled backlogs were zero. This run preceded the authentication connection-lifetime remediation; final-source repeat results must be identified separately.

| Measurement | n | p50 ms | empirical p95 ms |
| --- | ---: | ---: | ---: |
| authentication | 6 | 175.94 | 196.91 |
| investigation | 8 | 562.46 | 823.90 |
| policy_evaluation | 8 | 28.34 | 127.38 |
| approval_creation | 4 | 33.93 | 80.91 |
| approval_review | 4 | 31.03 | 55.63 |
| job_submission | 8 | 46.91 | 113.32 |
| submission_to_completion | 8 | 967.74 | 1365.14 |
| operations_overview | 8 | 48.77 | 243.40 |
| incident_detection | 8 | 19.80 | 35.83 |
| persisted queue_wait | 8 | 715.81 | 1077.24 |
| persisted worker_attempt_elapsed | 8 | 93.22 | 357.46 |
| persisted tool_execution | 48 | 7.69 | 13.85 |
| persisted search_policy | 8 | 10.21 | 16.54 |

Small-sample p95 is the nearest-rank empirical value, not a well-established tail distribution. No p99 is claimed. Forty-eight persisted successful tool timings cover eight investigations; executor timings exclude downstream source normalization. Worker-attempt elapsed time includes policy/authorization/execution and scheduler persistence, not mutation-only CPU time. Execution-event transaction timestamps are not used to manufacture elapsed latency. Queue and attempt timing use one PostgreSQL clock. The command `scripts/release_workload_measurements.py` reads only the bounded workload references with tenant predicates.

## Moderate finite queue and worker admission

```sh
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55433/northstar_demo \
  backend/.venv/bin/python scripts/release_queue_load.py --confirm-synthetic-demo
```

This separate harness refuses the primary DB and verifies the actual isolated backend is mock/development before creating fresh data. It creates five fictional tenants, four unique resources/jobs each, pauses only the isolated worker, submits 20 real policy-eligible jobs and makes one exact resource stale. It then scales the existing worker service to four containers, polls real PostgreSQL job state every 50 ms for at most 90 seconds, checks global ≤4/per-tenant ≤1 observed active work, and verifies 19 single committed note records plus one safe validation rejection. Cross-tenant job reads must fail. It restores the isolated worker to one container in `finally`.

This is a finite moderate queue with an intentional validation failure, not unlimited load. Sampling is not continuous observation; combine it with the admission transaction regression tests. Successful drain establishes lack of starvation for this cohort only. Oldest eligible due-time order is not strict round-robin fairness. Do not run alongside another workload or demonstration in the same isolated database.

## Final source repeat

The final coordinator passed the prospective concurrency-one target: 160/160 reads, zero errors, no endpoint p95 above 250 ms (maximum 44.83 ms for operations). Authentication had one 188.12 ms observation. This is a separate repeat, not substituted for the baseline. Fresh 60.000-second workload again completed eight workflows/four per tenant and four grants without failed or duplicate mutations. Persisted tool p50/p95 was 6.71/9.58 ms (n=48), search_policy 8.85/9.53 ms (n=8), queue wait 364.26/862.45 ms (n=8), and worker-attempt elapsed 79.06/110.04 ms (n=8). All empirical sample-size/scope limitations above still apply.

The final 20-job/five-tenant cohort drained in 8.575 seconds (24.748 seconds including setup): 19 single committed verified notes, one intended stale-evidence rejection, five foreign-job denials and zero duplicate or unauthorized mutations. Four configured worker processes reached an observed global peak of four and per-tenant peak of one; all five tenants terminated their four jobs. This supports only this bounded cohort's admission/no-starvation observation.

Final build filesystem sizes: static 1,136 KiB, standalone 57,772 KiB, uncompressed. No network transfer-size, per-route bundle, large-timeline stress or browser CPU rendering claim is inferred. Actual dashboard/timeline, loading/error/empty and pagination behavior is covered by browser/component tests and bounded existing APIs, rather than an invented frontend performance score.

The final explicit twenty-client target repeat also passed 160/160 reads, zero errors/target violations. Operations p50/p95 610.56/744.40 ms and investigation history 385.14/448.00 ms (20 samples each), below the prospective 1,500 ms per-endpoint p95 bound. Single login was 248.76 ms; no authentication tail claim. See EVIDENCE.json for endpoint counts, durations and throughput.
