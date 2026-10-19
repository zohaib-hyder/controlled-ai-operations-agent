# 0002 — Opaque authentication and explicit tenant repositories

Date: 2026-10-16. Status: accepted for Phase 1.

## Repository audit

Inspected Phase 0 commit `private-baseline`: seven business tables with tenant-aware composite foreign keys; six users with intended operator/approver/auditor roles but no credentials; one explicit migration; public health/readiness only; synchronous SQLAlchemy dependencies; a static Next.js shell; development Compose owner credentials; PostgreSQL-backed pytest, Vitest and Playwright foundations. Preserved that stack and the synthetic business dataset rather than rebuilding it.

## Decisions

Use Argon2id and high-entropy opaque sessions, with SHA-256 token digests in PostgreSQL. JWT claims and third-party identity providers add no value for this scope. Resolve role and tenant afresh on each request. Rotate the presented browser session after successful login; revoke on logout; enforce fixed expiry. Use explicit Origin validation for both auth writes, plus HttpOnly/SameSite cookies and production HTTPS validation.

Use globally unique normalized email for email-only login; a future shared identity/multiple membership design would need a separate account model. Migrate approvers to reviewers without changing IDs. Preserve business seed counts and add two admins only in explicit development auth seeding. Production mode refuses this fixture mechanism. Never commit a demo password.

Use database-backed email/client failure windows with transaction advisory locks rather than process-local counters, so protection persists across requests/workers. Proxy clients share the backend-observed address; production edge abuse controls remain necessary. Security events commit with session writes and have append-only application behavior, with its privileged-SQL limitation documented.

Defer RLS: the current database-owner connection bypasses ordinary policies. Adding policies without separate least-privilege roles and transaction-local context would be misleading. Use identity-bound repository predicates plus existing composite foreign keys and negative HTTP tests now; preserve RLS as future defense in depth.

Keep all business APIs read-only and reserve the requested permission names for future workflows. Frontend navigation uses returned permissions but confers no authority. Use a fixed-route same-origin Next.js proxy rather than cross-origin cookie/CORS complexity. Preserve the existing enterprise design and honest placeholders.

Migration `0002_authentication` is additive except for the intentional role/address normalization. Automatic downgrade is refused because dropping auth tables/hashes would discard security records; use a reviewed backup/migration plan instead. PostgreSQL's transactional DDL makes a failed upgrade roll back rather than partially merge identity data.
