# Phase Report Template

Copy and complete this template for each requested phase. Replace all placeholders with observed facts. Distinguish work completed from work planned and checks executed from checks not run. Do not treat this blank template as evidence of completion.

## Phase and scope

- Phase: <requested phase>
- Date: <YYYY-MM-DD>
- Authorized scope: <scope requested by the user>

## 1. What was implemented

<Describe completed behavior and deliverables.>

## 2. Files created and modified

| File | Change | Purpose |
| --- | --- | --- |
| <path> | <created / modified / deleted> | <purpose> |

## 3. Architecture decisions

<Record decisions, rationale, tradeoffs and references to the architecture and decision log. State “None” when applicable.>

## 4. Commands actually executed

| Command | Outcome / exit code |
| --- | --- |
| <exact command executed> | <observed result> |

## 5. Test results and failures

- Tests executed: <commands, scope and observed results>
- Failures: <failures and unresolved causes, or none observed>
- Checks not run: <checks and reasons>

Only report passing tests when the commands ran successfully. Mock tests alone do not establish production readiness.

## 6. Security and reliability concerns

<Describe relevant tenant isolation, schema validation, deterministic authorization, approval binding, revalidation, idempotency, transaction, injection/replay protection, execution bounds, audit and secret-handling findings. Identify unverified controls without claiming they exist.>

## 7. Remaining limitations

<List incomplete work, environmental blockers, unverified behavior and scope limitations. Identify deferred work without implementing unrequested phases.>

## 8. Git status and commit

- Git status: <actual observed status, or repository unavailable>
- Commit hash: <hash if committed; otherwise “Not committed”>
- Push / deployment: <actual actions; require explicit user instruction>

## 9. Verdict

**<PASS / PARTIAL / BLOCKED>**

<Explain the verdict against the requested scope and evidence. PASS means the requested phase scope is complete with required checks satisfied; PARTIAL means work remains; BLOCKED means a dependency prevents completion.>
