> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Tool contracts

All six tools are version `1.0`, classified `read`. GET `/api/v1/tools` returns authoritative JSON schemas and limits. Every model forbids extra fields and uses strict validation. UUID arguments are JSON strings; integers cannot be booleans, strings or fractions. List limits are 1–20. Arguments are at most 4,096 UTF-8 bytes and the complete invocation body at most 8,192 bytes.

| Tool | Permission | Arguments | Allowed output |
| --- | --- | --- | --- |
| get_customer | customer:read | customer_id UUID | customer_id, name, updated_at |
| get_account_status | account:read | account_id UUID | account_id, customer_id, status, block_reason, evidence_version, updated_at |
| get_ticket | ticket:read | ticket_id UUID | ticket_id, account_id, status, category, summary, duplicate_of_id, updated_at, evidence_untrusted |
| list_customer_tickets | ticket:read | customer_id UUID, limit default 10 | customer_id, items of ticket output, limit |
| list_recent_transactions | account:read | account_id UUID, limit default 10 | account_id, items of transaction_id/amount_minor/currency/status/created_at, limit |
| search_policy | account:read | query 2–240 characters, limit default 5 | items of policy_id/version/title/summary/relevance, limit, evidence_untrusted |

Ticket lists and transactions order by creation descending, then stable ID ascending. Ticket categories and 400-character summaries derive from existing synthetic records. Policy search uses up to eight distinct lowercase alphanumeric keywords, bound SQL parameters and deterministic match-count relevance. Results order by relevance, version and ID. Both historical policy versions can appear. Policy and ticket evidence never authorizes actions. Policy search output is bounded to 32,768 bytes, as is ticket listing; other tools are bounded to 16,384 bytes. Email addresses, transaction references, raw policy rules and ORM objects are excluded.

Example POST body (replace the ID with a customer from your authenticated tenant):

```json
{"tool_name":"get_customer","tool_version":"1.0","mode":"read","arguments":{"customer_id":"00000000-0000-0000-0000-000000000000"}}
```

The result envelope always has execution_id, tool_name, tool_version, status, data, error, started_at, completed_at, duration_ms and correlation_id. Success has structured data and null error. Failure has null data and a sanitized `{code,message}` error. Missing and foreign resources both produce `not_found` (404). Unsupported versions/invalid arguments are 422; unknown tools 404; missing permission 403; oversized input 413; rate/capacity limits 429; timeout 504; database/audit unavailability 503. Malformed outer requests use the existing standardized API validation envelope.

Operators, reviewers, admins and auditors currently share all three required read permissions, so all can inspect these six tools. No unauthorized privileged tool is exposed to auditors; filtering and execution denial are separately tested using a trusted test definition with a permission auditors lack.
