# Implementation architecture

These diagrams describe the implemented synthetic local application. AI planning never grants authorization; arrows do not imply an external customer integration.

## Overall system

```mermaid
flowchart TD
  Browser[Authenticated Next.js client] --> Proxy[Fixed route proxy]
  Proxy --> API[FastAPI auth / RBAC / tenant context]
  API --> Investigation[Request-scoped bounded orchestration]
  API --> PDP[Deterministic policy engine]
  API --> Approvals[Independent approval service]
  API --> Admission[Durable job admission]
  Investigation --> ToolExecutor[Typed read-only ToolExecutor]
  ToolExecutor --> DB[(PostgreSQL)]
  PDP --> DB
  Approvals --> DB
  Admission --> DB
  Worker[Python worker] --> DB
  Worker --> Execute[ControlledActionExecutor]
  Execute --> DB
  API --> Operations[Tenant-scoped operational read models]
  Operations --> DB
```

## Investigation lifecycle

```mermaid
flowchart LR
  Request --> Authorize[Validate current actor / tenant / scope]
  Authorize --> Bound[Reserve steps / calls / time / provider budgets]
  Bound --> Plan[Validated mock or optional provider decision]
  Plan --> Read[Authorized read-only tool]
  Read --> Normalize[Canonical evidence / provenance]
  Normalize --> Checkpoint[Persist result / counters / checkpoint]
  Checkpoint --> More{More bounded reads?}
  More -->|yes| Bound
  More -->|no| Findings[Grounded findings / advisory result]
  Checkpoint --> Stop[Cancel / limit / ambiguity: stop safely]
```

## Tool execution, evidence and policy

```mermaid
flowchart TD
  Selection[Static registered tool ID] --> Input[Strict schema input]
  Input --> Auth[Current session / permission / tenant]
  Auth --> Read[Scoped read-only transaction]
  Read --> Output[Validate bounded output]
  Output --> Evidence[Canonical sources / timestamps / citations]
  Evidence --> Reconcile[Conflicts / freshness / completeness]
  Reconcile --> Proposal[Exact action and arguments]
  Proposal --> PDP[Deterministic PDP with current policy versions]
  PDP --> Receipt[ALLOW / REQUIRE_APPROVAL / DENY receipt]
```

Tool timeouts, bounded outputs and no-progress limits constrain investigation. Source text is untrusted data, never an approval. Policy search supports retrieval; deterministic executable policy owns eligibility.

## Human approval

```mermaid
flowchart LR
  Proposal[Exact actor / tenant / action / resource / arguments] --> Decision[Policy decision and evidence versions]
  Decision --> Request[Persist approval request / binding / expiry]
  Request --> Reviewer[Different permitted human reviewer]
  Reviewer --> Review[Inspect evidence and reason]
  Review --> Grant[Approve or reject]
  Grant --> Revalidate[Execution rechecks reviewer grant / expiry / versions]
```

Some allowlisted low-risk actions can be allowed without approval; approval requirements come from deterministic policy, not the model. The executor remains authoritative even after approval.

## Controlled business execution

```mermaid
flowchart TD
  Intent[Bound execution intent + idempotency key] --> Lock[SERIALIZABLE transaction / resource and job locks]
  Lock --> Validate[Actor / tenant / evidence / policy / approval / resource version]
  Validate --> Fence[Check worker capability and lease fence when queued]
  Fence --> Savepoint[Allowlisted synthetic handler in savepoint]
  Savepoint --> Verify[Re-read exact effects and unchanged fields]
  Verify -->|valid| Commit[Atomic resource / receipt / audit / approval consumption]
  Verify -->|invalid| Rollback[Rollback business effects / record failure]
  Commit --> Replay[Same-key retry resolves existing outcome]
  Commit --> Uncertain[Lost commit acknowledgement requires reconciliation]
```

No external write integration exists. DB-level idempotency and transactional atomicity do not establish exactly-once network effects.

## Durable worker recovery

```mermaid
flowchart TD
  Queue[(Due durable jobs)] --> Claim[Capacity lock / SKIP LOCKED / claim attempt]
  Claim --> Lease[Owner / fence / heartbeat / 30-second lease]
  Lease --> Execute[ControlledActionExecutor revalidation]
  Execute --> Completed[Verified durable receipt / completed job]
  Lease --> Expiry[Worker loss / expired lease]
  Expiry --> Reconcile[Check existing receipt and durable state]
  Reconcile --> Retry[Eligible bounded retry / backoff]
  Retry --> Queue
  Reconcile --> Review[Ambiguous outcome: reconciliation required]
  Reconcile --> Dead[Exhausted attempts: dead letter]
```

Four global and one per-tenant admissions bound concurrency; one process handles one job at a time. Graceful shutdown drains bounded work. Recovery does not bypass an expired approval or stale evidence.

## Operations and incidents

```mermaid
flowchart LR
  Persisted[Jobs / attempts / receipts / audit / worker observations] --> Metrics[Role- and tenant-scoped operational aggregates]
  Metrics --> Dashboard[Operations Command Center]
  Metrics --> Detection[Deterministic incident thresholds]
  Detection --> Incident[Durable incident metadata]
  Incident --> Respond[Acknowledge / resolve with authorized reason]
  Persisted --> Trace[Exact correlation diagnostics]
  Trace --> Dashboard
  Respond --> Audit[Audit response metadata]
```

Resolving an incident does not repair a business resource, grant authority or authorize replay. See [implementation documents](../architecture/OVERVIEW.md) for historical phase evolution and [runtime limitations](../release/RUNTIME_REVIEW.md).
