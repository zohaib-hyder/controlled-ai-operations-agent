# 0001 — Bounded monorepo foundation

Date: 2026-10-16. Status: accepted for Phase 0.

Use a Python/FastAPI backend, PostgreSQL with SQLAlchemy 2.x/Alembic and Next.js/TypeScript/Tailwind frontend in a single repository. Use explicit migration and seed commands; keep startup free of schema mutation. Docker Compose supplies only these three services. Port 55432 avoids a pre-existing local PostgreSQL binding.

Use composite tenant-resource foreign keys rather than independent tenant and resource FKs, because independent keys allow cross-tenant relationships. Keep all business endpoints absent until authentication and authorization exist. Database credentials are privileged development credentials; composite constraints do not replace authenticated read isolation.

Use UUIDv5 fixture IDs, fixed timestamps, example.com emails and synthetic transaction references. Seed within one transaction, serialize with a PostgreSQL advisory transaction lock and insert missing IDs without overwriting changed rows. Test against a separate PostgreSQL database, not SQLite, to exercise actual constraints and migrations.

Use static seed-manifest counts in the UI and clearly label them. Do not imply connected tenant data or functioning agent/approval/audit features. Defer empty agent/integration/worker/policy/audit modules, real LLM adapters and authentication to requested later phases. `AI_PROVIDER=mock` reserves the intended default; no provider invocation exists.

Use dependency locks and separate lint, typecheck and build commands. Container runtime users are non-root; published ports bind loopback. No Redis, Kubernetes or agent framework is required. Base image tags and package-index supply chains are not fully hermetic; production hardening remains outside this phase.

Use the supported webpack build/dev mode because Turbopack CSS processing attempted a blocked local port operation in the verification sandbox, including after an elevated retry. This keeps one consistent build command across local and container environments.
