> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Action catalog, version 1.0

All definitions are static Python values. No imports, policy code strings or model-selected handlers are supported. The authenticated `/api/v1/actions` response exposes strict input schemas and only proposal-permitted actions.

| Action | Target | Required evidence | Eligible result | Prohibited conditions |
|---|---|---|---|---|
| create_customer_note | Customer | Current customer | ALLOW | Invalid/prohibited content; foreign target |
| add_ticket_note | Ticket | Current target ticket | ALLOW | Closed ticket; invalid/prohibited content |
| request_account_reactivation | Account | Account, complete transaction set, applicable policy | REQUIRE_APPROVAL | Security hold, ineligible block, unpaid/disputed ledger, conflicts |
| reactivate_account | Account | Account, complete transaction set, applicable policy | REQUIRE_APPROVAL | Same restrictions; only blocked/resolved_billing eligible |
| close_duplicate_ticket | Ticket | Both related tickets, duplicate policy | REQUIRE_APPROVAL | Unsupported relationship, foreign/different account, closed target |
| override_security_block | Account | Account | DENY | Always prohibited |

Every action requires `action:<name>:propose`, granted to operator, reviewer and admin. Auditor has none. No role has `action:<name>:approve` or `action:<name>:execute`.

Notes require only `content`, 5–500 characters; blank/injection/script/credential-pattern content denies. Account actions require an empty object. Duplicate closure requires exactly `duplicate_of_id` (UUID). Extra arguments deny and are discarded before persistence. Malformed outer request IDs, extra identity fields and oversized HTTP bodies are rejected before creating a proposal.

Unknown actions/versions produce auditable DENY proposals. Dynamic strings cannot add permissions or alter rules. Static catalog eligibility supplies note rules; no new synthetic policy rows are needed. Existing account-scoped `duplicate_ticket` records explicitly govern the related account's duplicate tickets.
