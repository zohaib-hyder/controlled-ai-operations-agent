> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Tenant isolation and RLS decision

## Boundaries implemented

- `current_identity` resolves the user, tenant, role and session ID from a validated token digest joined to the matching tenant/user. Session tenant and user IDs have a composite foreign key. Existing customer/account/ticket/transaction composite foreign keys remain intact.
- `TenantRepository` requires a server-created identity and adds `model.tenant_id == identity.tenant_id` to every list, count and detail query. Routes cannot accept arbitrary table names or tenant selectors. Lists have stable UUID ordering and bounded pagination.
- Client-supplied tenant/role query parameters are rejected on lists. Tenant/role headers are ignored for identity. Extra login fields are rejected. UUIDs from another tenant return the same response shape/message as unknown UUIDs, without an unscoped existence query.
- Misses record `resource_access_denied` under the requesting tenant and actor. This deliberately combines nonexistent IDs and cross-tenant attempts rather than probing a foreign tenant to classify them. It safely captures attempted access without introducing an existence oracle.
- Authentication lookup by globally unique normalized email and global opaque session digest necessarily precedes tenant resolution. Throttle keys are global infrastructure digests. These explicit authentication exceptions are not general business-data query paths.
- Seeding/migrations and test teardown are privileged administrative operations over synthetic data. The retained Phase 0 `find_account` helper explicitly accepts a tenant; new HTTP routes use the identity-bound repository.

## RLS evaluated and deferred

Phase 0 uses the same database-owner role for migrations and the application. Adding tenant policies over this bypass-capable connection would give misleading assurance. Full RLS requires a separately provisioned non-owner, non-BYPASSRLS runtime role, reviewed grants, FORCE ROW LEVEL SECURITY where appropriate, transaction-local tenant context, and tests for pooled-connection leakage and administrative operations. Those operational changes are not implemented superficially in this phase.

**No RLS is enabled or claimed.** The accepted tradeoff is explicit tenant predicates plus composite integrity constraints, no business mutations and extensive HTTP/repository isolation tests. A programming error that bypasses the repository could still read another tenant through the privileged connection; direct DB access is outside the application boundary. A future RLS implementation must preserve authentication bootstrap queries, migrations, seed operations and append-only event handling without introducing a bypass path for business reads.

See decision [0002](../decisions/0002-authentication.md). Tests verify both HTTP directions for customer/account/ticket IDs, pagination scope, spoofed tenant inputs, repository misses and session foreign keys. No RLS tests are represented as passed because RLS is deferred.
