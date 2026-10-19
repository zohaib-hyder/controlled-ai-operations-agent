> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Operations Command Center

Phase 10 adds operational read models and incident metadata. It never invokes business execution, approves actions, retries jobs or changes execution policy. The home page replaces static counts with authenticated database values; `/operations`, `/incidents` and `/diagnostics` provide expanded views. Existing investigation, approval and job pages remain available.

## Repository audit and sources

| Existing durable source | Operational use | Existing gap addressed |
| --- | --- | --- |
| Investigations, steps, checkpoints, events and evidence | Status cohorts, durations, volume, trace metadata | No aggregated overview; evidence payloads must not be copied into dashboards |
| ToolExecution | Validated invocation timeline and correlation | Raw observations are unnecessary for operations |
| ActionProposal and PolicyDecisionReceipt | Exact proposal/decision relationships | Decisions do not imply execution |
| ApprovalRequest/ApprovalDecision | Current queue, expiry, first-decision turnaround, rejection rate | Never infer approval from an LLM or dashboard state |
| ActionExecution and events | Actual committed/verified historical outcome references | No inferred success from a job or HTTP response |
| ExecutionJob, attempts, events and dead letters | Job cohorts, queue, retries, latency, lease expiry, incident conditions | Existing worker metrics were global logs, unsuitable as tenant API values |
| SecurityEvent | Safe operational/security timeline and denial bursts | No raw sessions, credentials or event payloads returned |

New durable sources are incidents, append-only incident events, tenant alert configuration, request-rate buckets and private worker observations. Migration `0009_operations` adds tenant FKs, unique detection keys, window/backlog/source/history indexes. Worker observations contain only process identifier, successful polling time and stopped flag; API health returns aggregate availability, never raw worker IDs or cross-tenant job information.

## Scope and access

Every API request revalidates the opaque server session and live user. Operators see only their own investigations/proposals/jobs/approvals and source-owned incidents; reviewers, administrators and auditors see tenant operational metadata. This deliberately does not broaden existing business-resource or investigation-content endpoints. Only reviewers/administrators respond to incidents. Only administrators configure alert thresholds. Frontend controls are supplementary to backend authorization.

Reads use a repeatable-read snapshot and statement/lock timeouts. Rate accounting commits in a separate small transaction to avoid upsert conflicts inside the read snapshot; limits are 120 reads and 30 mutation requests per actor/minute. Collections cap limit at 50 and offset at 10,000. Details cap history and traces explicitly. Strict contracts reject forged scheduling, role, tenant and response fields. No external monitoring or notification delivery was added.
