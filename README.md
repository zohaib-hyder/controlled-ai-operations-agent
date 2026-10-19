# Controlled AI Operations Agent

A synthetic enterprise-operations application demonstrating how an AI-assisted investigation can lead to a controlled, independently approved business action. Built as a Forward Deployed Engineering portfolio project for fictional **Northstar Services**.

**Release status: Phase 12 PARTIAL.** Backend/worker images are not accepted for release: local image and vendor-SBOM profiles contain **16 unique unresolved High CVEs**. Source-publication review is separate from container release acceptance. Nothing is deployed. See [runtime security review](docs/release/RUNTIME_REVIEW.md) and [publication checklist](docs/portfolio/GITHUB_PUBLICATION_CHECKLIST.md).

## Business problem

Support teams need to reconcile tickets, account restrictions, payments and operational policy before changing customer state. An unconstrained assistant can mistake persuasive ticket text for authority, miss a security block or repeat a write after a timeout. This project makes the authorization and execution boundaries inspectable.

## Implemented capabilities

- Session authentication, role permissions and tenant-bound data access.
- Bounded read-only investigations with validated tools, persistent checkpoints and cancellation.
- Canonical evidence, provenance, policy search, freshness checks and conflicting-evidence reporting.
- Deterministic policy decisions and exact action proposals.
- Independent human approval bound to actor, tenant, action, resource, arguments and evidence/policy versions.
- Synthetic PostgreSQL writes through ControlledActionExecutor, with immediate revalidation, idempotency, transactional verification and receipts.
- Durable PostgreSQL jobs, fenced leases, bounded retries, reconciliation and dead-letter visibility.
- Operations Command Center, incidents, correlation diagnostics and adversarial evaluation tooling.

The agent investigates; backend code authorizes writes. The deterministic mock provider is the default. The optional LLM adapter has **no verified live-provider behavior**. There are **no real enterprise write integrations**, real customer data, adoption claims or production deployment.

## Architecture and stack

```mermaid
flowchart LR
  Operator --> UI[Next.js / TypeScript / Tailwind]
  UI --> Proxy[Fixed same-origin proxy]
  Proxy --> API[FastAPI / Pydantic]
  API --> Agent[Bounded read-only state machine]
  Agent --> Tools[Authorized typed tool executor]
  Tools --> DB[(PostgreSQL / SQLAlchemy / Alembic)]
  API --> PDP[Deterministic policy engine]
  Reviewer --> API
  API --> Approval[Independent approval]
  Approval --> DB
  API --> Jobs[Durable job admission]
  Jobs --> DB
  Worker --> Executor[ControlledActionExecutor]
  Executor --> PDP
  Executor --> DB
  DB --> Ops[Operations read models / incidents]
```

Python/FastAPI/Pydantic, PostgreSQL/SQLAlchemy/Alembic, Next.js/TypeScript/Tailwind, Docker Compose, pytest, Vitest, Playwright and GitHub Actions. No agent framework, Redis or Kubernetes. [Seven implementation diagrams](docs/portfolio/ARCHITECTURE.md) and [engineering case study](docs/portfolio/CASE_STUDY.md) explain the boundaries.

## Controlled lifecycle and security model

Operator request → current-session authorization → bounded evidence retrieval → deterministic policy evaluation → exact proposed action → independent approval when required → revalidation → controlled execution → verification → append-only application audit events.

Tenant and role authority comes from validated backend identity. LLM output, ticket prose and UI visibility cannot grant permission. Tools have strict input/output schemas; no agent shell, arbitrary code, unrestricted HTTP or general SQL tool exists. Execution binds exact versions and rechecks authority/resource state immediately before mutation. Serializable transactions, fencing and idempotency prevent duplicate local effects. Append-only application records are **not** a tamper-proof external ledger. PostgreSQL RLS and production DB least privilege remain future work.

## Reliability and evaluation evidence

Historical verified private-baseline results, retained with their original scope:

| Check | Observed result |
| --- | --- |
| Backend regression | 727 passed; one upstream warning |
| Versioned evaluation catalog | 601/601 scenarios |
| Frontend Vitest | 50 passed |
| Browser | 64 passed: 52 default, 4 release, 8 negative |
| Graceful restart recovery | Queued job completed; one receipt/record; zero duplicate mutations |
| Final image profiles | Backend/worker each 0 Critical / 55 High / 54 Medium; frontend 0 Critical / 0 High / 3 Medium |

The duplicated backend/worker High matches represent 14 unique image CVEs; a separate vendor-SBOM profile adds two PCRE2 High CVEs. No findings are suppressed. [New publication-copy checks](docs/phases/PHASE_13A.md) are reported separately; baseline results are not silently attributed to this copy.

## Actual synthetic execution evidence

![Verified synthetic durable execution with before/after receipt](docs/portfolio/assets/controlled-execution-jobs.png)

Actual publication-copy screen from a passed local browser workflow. It shows a synthetic committed action, not release acceptance or production deployment. [Capture inventory](docs/portfolio/SCREENSHOTS.md).

## Local setup

Prerequisites: Docker Compose v2 (including `!override` support), Python 3.12 with uv, and Node 26.12.0 for host frontend checks. Node 26 is Current; this local-demo qualification is not a production LTS recommendation.

From the prepared snapshot directory:

```sh
cp .env.example .env
python3 scripts/create_demo_credentials.py
docker compose config --quiet
docker compose build
docker compose up -d db
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.db.seed_auth
docker compose up -d --wait backend frontend worker
curl --fail http://127.0.0.1:8000/api/v1/health
curl --fail http://127.0.0.1:8000/api/v1/ready
```

Open `http://localhost:3000/login`. Use fictional `operator.0@example.com`, `reviewer.0@example.com` or `auditor.0@example.com` with the password generated only in your ignored `.env`. Use separate browser contexts for independent actors. Never record the password. The public synthetic DB placeholder is disposable/local only. No public clone URL exists yet.

The publication copy defaults to a distinct Compose project name to avoid sharing the private repository's volume; published ports still conflict if both stacks use defaults. Stop the other stack or use a separate port override. Follow [DEMO_GUIDE](docs/portfolio/DEMO_GUIDE.md) for fixtures, policy, approval, worker execution, audit and recovery.

## Development checks

```sh
uv sync --project backend --frozen --extra test
docker compose exec -T db createdb -U northstar northstar_test
# From backend; dedicated disposable DB only:
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test uv run --frozen pytest -q
# From frontend:
npm ci --no-audit --no-fund --update-notifier=false
npm run lint
npm run typecheck
npm test
NEXT_TELEMETRY_DISABLED=1 npm run build
```

Run heavy suites serially. See [demo/evaluation commands](docs/portfolio/DEMO_GUIDE.md). GitHub Actions is configured; hosted execution is not claimed. Dependency downloads are distinct from project metadata uploads; automatic npm audit and Next telemetry are disabled locally. Do not run external scanners or opt into real LLM calls as part of this demo.

## Known limitations and publication

Phase 12 remains PARTIAL. Unresolved native-library High CVEs, Current-channel runtime maintenance, unverified live LLM behavior, no external writes, no production identity provider, no RLS, and limited synthetic/local load measurements prevent production claims. Graceful queued restart does not establish crash-at-commit safety or external exactly-once effects. Historical transient agent wall-budget failures remain disclosed; the eight-second bound was not relaxed. See [complete limitations](docs/release/KNOWN_LIMITATIONS.md).

[Case study](docs/portfolio/CASE_STUDY.md) · [Architecture](docs/portfolio/ARCHITECTURE.md) · [Demo](docs/portfolio/DEMO_GUIDE.md) · [Publication checklist](docs/portfolio/GITHUB_PUBLICATION_CHECKLIST.md) · [Contribution guidance](CONTRIBUTING.md) · [Security disclosure](SECURITY.md) · [License review](docs/portfolio/LICENSE_REVIEW.md).

This snapshot intentionally has no inherited Git history. Owner-authored material is [MIT licensed](LICENSE), with [third-party terms retained separately](THIRD_PARTY_NOTICES.md). The exact public author/committer identity is owner-approved for one initial local commit after audit. No push, publication or deployment is authorized by this preparation.
