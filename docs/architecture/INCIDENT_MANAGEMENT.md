> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Operational incident management

Incidents are metadata, not business approvals or repair commands. Composite tenant FKs bind source jobs/approvals, visible source actor and optional active assignee. Safe generated titles/descriptions contain no customer/ticket content. Notes are bounded, HTML-escaped in the UI and reject obvious credential assignments. Notes remain operator-entered text, not a secret-storage mechanism.

## Detection

The worker performs bounded periodic detection after successful job polling (30-second cadence, up to five tenants per page, continuing by stable tenant UUID). Each rule selects at most 25 previously unreported sources per tenant; subsequent cycles advance beyond existing incidents. Unique tenant/condition keys plus `INSERT ... ON CONFLICT DO NOTHING` deduplicate races and repeated discovery. Reads and dashboard refreshes never create incidents. Reviewers/administrators can explicitly run the same detector through a CSRF-protected endpoint.

| Condition | Deterministic rule | Dedup key |
| --- | --- | --- |
| Dead letter | Current DEAD_LETTERED job | category + job ID |
| Uncertain outcome | Current RECONCILIATION_REQUIRED job | category + job ID |
| Repeated lease expiry | ≥3 lease_expired events for a job in trailing 24h | category + job ID |
| Persistent failure | ≥3 FAILED jobs created in trailing 24h for an actor | category + actor + UTC date |
| Authorization burst | ≥5 attributed denied audit events in trailing 5m | category + actor + five-minute UTC bucket |
| Approval workflow failure | INVALIDATED approval updated in trailing 24h | category + approval ID |

Expiration alone is normal lifecycle and does not automatically create an approval-failure incident. Anonymous unattributed failures are not assigned fabricated actor identities. Actual source-event IDs are retained where available; missing event references remain null. Batch selection excludes existing conditions before applying limits, so old sources cannot starve new discoveries.

## Response

OPEN → ACKNOWLEDGED → INVESTIGATING → RESOLVED → CLOSED; ACKNOWLEDGED may resolve directly. No reopening. Assignment and notes do not change lifecycle state. Closed incidents reject further changes. Only current reviewers/admins can acknowledge, assign, investigate, resolve, close or add notes. Assignees must be active same-tenant reviewers/admins. Every change appends an incident event and security audit event atomically. Source actors can inspect their permitted incidents; auditors read tenant history without mutation rights.

Resolution records the review outcome; it does not retry a job, consume an approval, repair a resource, clear a security hold or declare an uncertain execution successful. Backlog alerts remain active until the underlying job condition actually changes. A condition stays deduplicated after resolution/closure; source-level recurrence is visible in job events/alerts, without automatic reopening. This is an explicit local design limit.

## Runbook

1. Inspect source entity, immutable execution receipts, attempts and correlation trace.
2. Acknowledge and assign an active authorized reviewer; keep credentials out of notes.
3. Investigate policy/approval/version or infrastructure causes through existing read-only evidence.
4. Record resolution accurately, including remaining restrictions. Use existing separately authorized job controls only if appropriate; incident response never invokes them.
5. For uncertain outcomes preserve reconciliation-required state until transaction evidence proves the outcome. Never infer success from resolving an incident.

Incident detail displays the latest 25 durable history events in chronological order; older events remain persisted. There is no dedicated history pagination endpoint in this phase.

ORM hooks enforce application append-only incident history. Database-owner SQL, backup/restore tampering and production database privilege separation remain outside this portfolio guarantee.
