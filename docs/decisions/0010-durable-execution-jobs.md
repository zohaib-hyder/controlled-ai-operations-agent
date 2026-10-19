# 0010: PostgreSQL durable execution scheduling

Accepted for Phase 9. Retain one controlled business mutation implementation and its atomic receipts. Add PostgreSQL job metadata, short claims, fenced bounded leases and receipt reconciliation. Use a stored submitter capability independent of cookie lifetime while checking current actor authority. Preserve reviewer grant validity. Avoid Redis, external brokers, generic distributed frameworks and external write integrations.

A separate metadata completion transaction deliberately allows a crash after business commit; reconciliation proves the outcome from atomic immutable receipts. This is preferable to claiming that a worker transport response determines success. Explicit ambiguous state and bounded retries preserve safety. Global/per-tenant scheduling uses a small advisory-lock-protected capacity decision and SKIP LOCKED; suitable for a synthetic portfolio, not a claim of high-volume production readiness.
