> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Operational metrics and safe health

## Window semantics

Preset windows are trailing 24 hours, 7 days or 30 days from PostgreSQL UTC clock. Custom dates require explicit UTC offsets, a positive interval and at most 31 days. Historical cohorts use half-open `[start,end)` **creation timestamps**. Cohort statuses and available decisions are observed as of the consistent read snapshot; a historical creation cohort is not a reconstruction of its past status. UTC daily buckets are clipped to the requested interval and include zero-valued days (maximum 32 buckets). Empty rates and duration statistics are null, never invented zero averages.

Current backlog gauges intentionally ignore the creation filter: pending unexpired approvals, approvals expiring in the next 15 minutes, nonterminal incidents, queued/retry/claimed/running jobs, current dead letters, reconciliation-required jobs and oldest active queue age. This includes older unresolved work. The UI labels this distinction. Current backlogs use selective tenant/status indexes, not unbounded historical payload retrieval.

## Definitions

| Metric | Exact definition |
| --- | --- |
| Investigation volume/distribution | Creation-cohort row counts by current status |
| Completion rate | COMPLETED investigations / all investigations in cohort |
| Investigation duration | completed_at − started_at for cohort rows with both timestamps; count, mean, p50, p95 seconds |
| Approval turnaround | First APPROVED/REJECTED decision time − request creation; one sample per request cohort |
| Approval rejection rate | Distinct REJECTED requests / distinct APPROVED or REJECTED requests in request cohort |
| Job success | COMPLETED / (COMPLETED + FAILED + DEAD_LETTERED) within job creation cohort; uncertain and cancelled work excluded |
| Retry rate | Distinct cohort jobs with a retry transition within the selected window / all cohort jobs |
| Retry trend | Retry transitions by UTC event day; duplicate-submission events excluded |
| Dead-letter rate | DEAD_LETTERED cohort jobs / all cohort jobs |
| Queue depth/age | Current QUEUED, RETRY_SCHEDULED, CLAIMED or RUNNING jobs; age of oldest created row, null if empty |
| Reconciliation/dead-letter backlog | Current job status gauges, independent of historical cohort |
| Execution latency | Finished job attempt time − claim/attempt creation, including failed attempts; sample count, mean, p50, p95. Direct executions without jobs do not produce these samples |
| Lease expirations | Durable lease_expired job events within selected event window |

All aggregates include tenant and role ownership predicates. No LLM determines metrics. The overview uses a fixed query count (tested ≤35 SQL statements) and no per-row ORM fetching. Timeline source queries cap their own top `(limit+offset)` rows before a stable bounded union. SQL explain checks exercise queue lookup; small synthetic fixtures may correctly use sequential plans rather than forced indexes.

## Health

Public health remains process liveness; public readiness verifies PostgreSQL connectivity and returns a safe 503 on outage. Authenticated overview adds API/database accessibility, exact migration compatibility, recent successful worker polling, and queue processing condition. A worker process being up is not sufficient: its persisted successful observation must be within the tenant-configured 45-second default threshold. Graceful stop records unavailable immediately; hard kills become unavailable after staleness. Never-observed workers are unknown. Dead letters, uncertain outcomes, expired active leases and excessive queue age degrade queue health. Unknown/unavailable worker or incompatible migration degrades overall health.

Database/authentication outage prevents a private snapshot; API 503 and the UI unavailable state replace healthy cards. No infrastructure connection strings, tokens or exception bodies are returned. Availability describes the shared worker pool, not another tenant's work. There is no external LLM dependency check because these operational queries do not call an LLM.

Tenant-configurable thresholds: dead-letter backlog, reconciliation backlog, queue age, worker staleness, terminal failure percentage and minimum terminal sample count. Alerts show actual comparisons; changing thresholds never changes policy, execution budgets or incident response. Historical failure-rate alerts use the selected cohort, while infrastructure/backlog diagnostics reflect current state.
