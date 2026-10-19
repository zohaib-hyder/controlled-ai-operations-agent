> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Authorization

`backend/app/core/permissions.py` is the centralized backend permission model. Authenticated identity is immutable for one request and resolved from the current server-side user/session. Role changes or user deactivation affect subsequent requests; no permission or tenant claim is accepted from a cookie payload, request body, query parameter or tenant/role header.

| Permission | operator | reviewer | admin | auditor |
| --- | --- | --- | --- | --- |
| customer:read | Yes | Yes | Yes | Yes |
| account:read | Yes | Yes | Yes | Yes |
| ticket:read | Yes | Yes | Yes | Yes |
| investigation:create | Yes | Yes | Yes | No |
| approval:review | No | Yes | Yes | No |
| user:manage | No | No | Yes | No |
| audit:read | No | No | Yes | Yes |
| settings:manage | No | No | Yes | No |

`require_permission` is a reusable FastAPI dependency. It denies unknown permissions/roles by default, records permission denials and returns a structured 403. Every customer, account and ticket route requires its read permission before constructing a tenant repository. Pagination limits are 1–100 and offsets 0–10,000; unknown list query parameters, including tenant or role overrides, are rejected. Detail IDs must be UUIDs. A missing or cross-tenant record returns the same 404 message.

The non-read permissions reserve semantics for later phases; they do not create functionality. There are no investigation, approval, user-role-management, audit-read or settings-write APIs yet. In particular, operators cannot grant themselves roles, and admins have no role-mutation endpoint to misuse across tenants. All four roles are read-only for business records in this phase. Tests exercise the permission dependency through test-only routes that are absent from the running application.

The frontend obtains permissions from `/auth/me` to filter navigation and show an access-denied state for direct unauthorized page navigation. These checks are presentation only. Static placeholder HTML contains no protected records. Authenticated data is fetched only through backend-protected APIs. UI state is reset when the authenticated session/role changes, and it never stores session tokens in localStorage.

Security events are append-only through application code. ORM instance updates/deletes are rejected; no event mutation or public audit endpoint exists. This is not a tamper-proof database ledger: privileged raw SQL/bulk operations could bypass ORM hooks. Database least privilege and stronger immutable audit infrastructure remain future work. Login and session-control writes are deterministic backend code, with no LLM decisions or agent involvement.

## Phase 7 proposal permissions

Operator, reviewer and admin receive six `action:<catalog-name>:propose` permissions. Auditor receives none. No action approval or execution permissions are granted. The existing generic approval review permission does not grant approval capability. No self-approval is possible because there are no approval grants or endpoints. Action proposals derive actor and tenant from the authenticated session and use creator-scoped investigation/receipt access. Current session and role are revalidated during every evaluation. Permission changes invalidate earlier eligibility bindings; revoked sessions receive 401.

## Phase 8 execution and review

Operator/admin receive `action:execute`; reviewer/admin receive `action:approve`. These are distinct from catalog proposal permissions. Execution is restricted to the original proposal creator. Same-tenant active reviewers must differ from creator/requester, including admins. Current actor authorization and the original reviewer's role/session validity are checked again in the controlled transaction; no planner claim or approval-body identity is trusted. Public investigation access remains creator-scoped; only the explicit internal approval-review path can retrieve another actor's cited evidence for an authorized reviewer.
