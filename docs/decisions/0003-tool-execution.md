# 0003 — Read-only tool execution integration

Date: 2026-10-16. Status: accepted integration plan before implementation.

Audit: Phase 1 provides validated Identity dependencies, a centralized permission map, TenantRepository predicates, structured errors/request IDs, synchronous SQLAlchemy session factories, append-only application security events, isolated PostgreSQL tests, and a fixed-route Next.js proxy. Preserve these components. Tickets have subject/body/status but no category; derive a documented category and bounded summary instead of changing historical business records. Policy keys/descriptions supply titles/summaries.

Plan: static allowlisted tool definitions with strict Pydantic contracts; immutable server-resolved execution context; scoped repositories; a bounded worker pool; read-only handler transactions with PostgreSQL statement/lock timeouts; independent transactional execution metadata and per-actor admission counters. Revalidate the authenticated session and current role before constructing context. Never accept scope/permissions in arguments. The HTTP adapter and future trusted Python callers use the same executor, without internal HTTP calls.

A coroutine timeout cannot safely kill arbitrary synchronous Python. Keep the worker slot occupied until cleanup actually finishes, signal cancellation cooperatively, discard late outputs and use database statement timeouts. Trusted built-in handlers are bounded database reads. This is not a Python sandbox; do not register untrusted handlers. No retries, business writes, agent, LLM selection, approval execution, external fetch, vector infrastructure or Phase 3 functionality.

Persist only execution metadata, never arguments/results/passwords/tokens. Reuse Phase 1 CSRF checks and same-origin routing. Retain the documented RLS/privileged-database-role limitation rather than claim database isolation beyond explicit predicates and composite foreign keys.
