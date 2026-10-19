# Case study: controlled AI-assisted operations

## Problem and discovery assumptions

Northstar Services is fictional. The discovery scenario assumes operators spend time joining support tickets, account restrictions, payments and policy versions before deciding whether an account can be reactivated or a duplicate ticket closed. There were no customer interviews, customer deployment, testimonials, adoption, revenue or business savings measurements.

The simulated requirements were inspectable reasoning, tenant isolation, deterministic write authority, independent approval, safe replay and operational diagnosis. Fixture scenarios cover unpaid billing, security review, duplicates, eligible reactivation, conflicting evidence and cross-tenant requests. Every customer and transaction is synthetic.

## Delivery stages

Phases 0–2 established the monorepo, PostgreSQL migrations, synthetic fixtures, sessions/RBAC and strict read-only tools. Phases 3–6 added bounded planning, persistent checkpoints, provenance, evidence reconciliation and observation-driven tool selection. Phases 7–8 introduced the deterministic Policy Decision Point, exact proposals, independent approvals and verified local writes. Phases 9–10 added durable PostgreSQL jobs, leases/fencing, retry/reconciliation, operations metrics and incidents. Phase 11 added a versioned adversarial catalog; Phase 12 added browser, local performance, restart and image-security evidence. Phase 12 remains PARTIAL. This publication copy is separate from the private development history.

## Architecture decisions

A custom bounded Python state machine exposes step/call/time/token/cost limits without an additional orchestration framework. Investigation tools remain read-only. FastAPI/Pydantic enforce contracts; SQLAlchemy repositories and composite tenant foreign keys constrain scoped access. PostgreSQL owns durable state, transactions, checkpoints and the job queue. A separate worker invokes the same controlled executor used by synchronous local execution. Next.js presents evidence and permission-aware controls through a fixed same-origin proxy.

Using PostgreSQL rather than adding a broker keeps the local demo reproducible, but conservative tenant serialization and polling limit throughput. Deferred RLS and the privileged development connection are explicit limitations. Immutable application receipts are not an external tamper-resistant audit service.

## Authorization and execution boundary

LLM text never approves a write. Canonical evidence records source identity, version and collection time; conflicts and stale facts can block eligibility. The deterministic PDP returns ALLOW, REQUIRE_APPROVAL or DENY. Human approval binds the exact actor/tenant/action/resource/arguments and evidence/policy versions. Self-review is rejected when independent approval is required.

ControlledActionExecutor revalidates current authority, approval, policy, resource state and worker fence inside a locked serializable transaction immediately before mutation. A savepoint permits verification failure to roll back business effects. Receipts, approval consumption, synthetic business changes and audit events commit together. Same-key replay returns the durable result. Uncertain commit acknowledgement requires reconciliation rather than blind retry.

## Reliability engineering

Jobs persist actor-bound intent and idempotency. Database-time leases, fencing, attempts, bounded backoff and receipt reconciliation constrain recovery. Four global/one per-tenant admission caps prevent a tenant taking every slot. Dead letters and reconciliation-required states are visible; incident acknowledgement changes operational metadata only. Graceful shutdown permits bounded in-flight processing. No claim of strict scheduling fairness, OS-kill-at-commit verification or external exactly-once effects is made.

## Evaluation methodology and measured outcomes

Historical private-baseline results: **727 backend tests**, **50 Vitest tests**, **64 browser cases** (52 default, four release, eight negative), and **601/601 versioned evaluation scenarios**. The scenario catalog overlaps underlying regression/evaluation cases; it is not 601 additional independent end-to-end customer workflows. Backend tests had one upstream warning. Mock AI and synthetic PostgreSQL data were used; no live LLM evaluation was performed.

Browser cases used actual application HTTP/DB/worker flows on desktop/mobile with retries disabled. Restart recovery preserved a durable snapshot and completed a queued job with one receipt/one record and zero duplicate mutations. These results are local measurements with explicit denominators, not production reliability guarantees. [Publication-copy checks](../phases/PHASE_13A.md) are separate.

A local read benchmark used 20 samples per endpoint, not enough for p99. At 20 configured clients the initial cohort had 69 errors/160 requests from pool starvation: authentication held a DB connection while route handlers requested another. Closing the authentication session before returning immutable identity removed that retention; the repeated cohort succeeded 160/160, with slowest endpoint p95 **687.30 ms** versus **3267.66 ms** before. This is a small local cohort, not sustained production capacity or an SLA. See [measurement methods](../release/PERFORMANCE_BASELINE.md). Historical transient investigation wall-budget failures remain disclosed; their root cause is not proven and the eight-second limit was not relaxed.

## Security tradeoffs and release decision

Egress-disabled Grype scans found 55 High matches per backend/worker image: 110 duplicated matches represent 14 unique CVEs. A separate vendor-SBOM profile identified two more High PCRE2 CVEs in Psycopg's loaded private library. The latest observed wheel still bundles it; a vendor fix exists but a replacement native-linking strategy has not been qualified. Severity alone does not prove app reachability, and absence of a listed stable distro fix does not imply safety.

Frontend runtime moved to official Node 26.12.0/OpenSSL 3.5.9 and removed unused JS package managers. Current-channel maintenance is a tradeoff, not an LTS production endorsement. Full-image frontend counts are zero Critical/High and three Medium; scanner package matching cannot guarantee coverage of embedded components. [Full advisory/exposure inventory](../release/RUNTIME_REVIEW.md) is retained, unsuppressed.

An earlier npm auto-audit sent dependency metadata, and possible telemetry from an aborted build cannot be ruled out. That historical exception is not erased. Subsequent scans used disabled networking; npm audit/telemetry defaults and Next build network isolation were corrected. Publication preparation uses local tools and no external project scanner.

## Limitations and future work

Phase 12 is **PARTIAL**, and backend/worker images are not accepted for release. Future work includes supported native-library remediation and requalification, maintained runtime lifecycle decisions, production DB least privilege/RLS, external audit durability, identity-provider integration and any real write adapter with its own reconciliation protocol. Live-provider behavior requires separate controlled evaluation. The owner approved MIT and the public author name Zohaib Hyder. The public Git email is now approved for one initial local commit. Publication still requires separate explicit authorization. No production deployment is claimed.
