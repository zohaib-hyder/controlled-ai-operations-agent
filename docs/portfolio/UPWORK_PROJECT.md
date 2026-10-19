# Upwork portfolio draft — not published

**Title:** Controlled AI Operations Agent: Policy, Approval and Reliable Execution

**Business problem:** A fictional support team needs to combine account, billing, ticket and policy evidence before changing customer state. The engineering challenge is to make each decision inspectable and prevent unauthorized, stale or duplicated mutations.

**Delivered solution:** A multi-tenant operations application with bounded read-only investigations, provenance and policy search, deterministic action eligibility, independent approval, verified synthetic local writes, durable jobs and operational diagnostics. Implemented as a standalone portfolio simulation, not paid client delivery.

**Engineering approach:** Strict typed tool contracts; backend-owned authorization and tenant scope; exact version-bound approvals; immediate execution revalidation; serializable transactions; idempotency and receipts; fenced worker leases and bounded recovery. No LLM-generated permission or general-purpose shell/SQL tool.

**Technologies:** Python, FastAPI, Pydantic, PostgreSQL, SQLAlchemy, Alembic, Next.js, TypeScript, Tailwind, Docker Compose, pytest, Vitest, Playwright and GitHub Actions configuration.

**Measurable local evidence:** Private-baseline 727 backend tests, 50 frontend unit tests, 64 browser cases and 601/601 evaluation scenarios. Graceful restart verification completed a queued synthetic job with one receipt/record and zero duplicate mutations. Publication-copy checks have their own phase report. No savings, revenue, customer scale or uptime metrics were measured.

**Limitations:** Synthetic data and mock AI by default; live LLM behavior unverified; no real enterprise writes or production deployment. Phase 12 release gate remains PARTIAL with 16 unique unresolved High CVEs across image/SBOM profiles. Source-publication approval is separate from container release acceptance.

**Media:** Reviewed actual screens and architecture diagrams only; consult SCREENSHOTS.md. No repository/deployment link until expressly authorized.
