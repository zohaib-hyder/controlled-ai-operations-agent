> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Browser acceptance coverage and gaps

The verified inventory is 52 default cases (48 baseline plus four job-state cases), four release cases and eight isolated negative cases: 64 unique viewport cases. The final coordinator passed 52 default, four primary release, four repeated isolated release and eight negative cases: 68 executions across 64 unique viewport cases. The new complete journey is one end-to-end business scenario tested in two viewport configurations. Counting many assertions inside it as separate independent journeys would inflate coverage. Repeated executions against primary and clean stacks are reported separately.

The release journey performs real sign-in, investigation, evidence/trace/reconciliation display, UI proposal/PDP, independent review, durable submission, worker completion, own-job receipt inspection, account-version increment, same-key replay, different-key conflict, auditor diagnostics and foreign-tenant API/UI denials. It uses fresh records, isolated role contexts and no HTTP mocks. An executor is an operator with execution permission, not an invented fifth stored role.

| Required negative case | Browser coverage | Remaining evidence boundary |
| --- | --- | --- |
| Self approval | Hidden control + actual backend 403 in release journey | Operator lacks review permission; admin/requester self-approval invariants also tested in backend corpus |
| Expired approval | Isolated real expired-approval UI/backend case | Passed in final fresh coordinator |
| Revoked permission | Isolated actor role revocation, Access denied UI and backend 403 | Separate real expired-session case checks sign-in recovery and 401; final fresh execution required |
| Foreign investigation/approval/job | Actual foreign context API 404s; foreign detail/list UI assertions in final release journey | Passed in final fresh coordinator |
| Policy DENY/security override | Real administrator UI evaluation, DENIED reasons, no execute control, account snapshot unchanged | Does not prove every policy branch |
| Conflicting evidence | Existing real investigation browser case | Broad conflict corpus remains backend-only |
| Stale decision | Isolated real policy-version fault, INVALIDATED UI and backend 409 | Passed in final fresh coordinator |
| Duplicate execution | Same job on exact key; different key 409; account version unchanged | No external-system exactly-once claim |
| Worker unavailable | Old cancellation cohort intentionally stops worker and observes queued work | Queued timeline and unchanged business snapshot while worker is stopped; no dedicated unavailable-status dashboard |
| Reconciliation required/dead letter | Prepared actual job fixtures, exact-state UI, unrelated admin retry 403 and unchanged business/approval/job snapshot | Passed in final fresh coordinator |
| Incident resolution | Reviewer browser response and auditor denial plus unchanged business/approval/job snapshot | Passed in final fresh coordinator |

Some older tests deliberately mock error HTTP responses for UI error-state behavior; they are not evidence for the primary complete business journey. Reports must distinguish those cohorts. No blind retries or arbitrary synchronization sleeps are added to the release suite. A test-selector failure is preserved rather than counted as an application authorization failure.

Inventory additions do not waive final verification or the rebuilt-image security scan gate. No Phase 13 work is authorized.

After the explicit logout-synchronization correction, a fresh full-inventory repeat passed 52 default + four primary release + eight isolated negative cases. Final coordinator plus this repeat: 132 passing executions, 64 unique viewport cases, six full-journey executions of one business scenario. Separately retain the failed repeat (51 passed/one mobile role-switch failure). No retries or skips hid it.
