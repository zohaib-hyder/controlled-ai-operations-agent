# Project 4: Controlled AI Operations Agent

## Role, scope and purpose

Act as the principal software engineer implementing a standalone Forward Deployed Engineering portfolio application for LinkedIn, Upwork and GitHub evidence.

Work only in this separate `controlled-ai-operations-agent-publication` snapshot; preserve the original repository unchanged. All customer, ticket, account and policy data must be synthetic. Do not connect to real customer systems.

## Stack

- Python, FastAPI and Pydantic.
- PostgreSQL, SQLAlchemy and Alembic.
- Next.js, TypeScript and Tailwind.
- Docker Compose, pytest, Vitest, Playwright and GitHub Actions.
- A custom bounded Python agent state machine.
- A deterministic mock AI provider by default; real LLM use is optional and configured through environment variables.

## Core workflow

Operator request → authorized investigation → evidence retrieval → policy evaluation → proposed action → human approval when required → revalidation → controlled execution → verification → immutable audit events.

## Mandatory engineering rules

1. All tenant-scoped records, queries and tool calls must enforce tenant isolation.
2. All tool inputs and outputs require strict schemas and validation.
3. Never trust LLM-generated authorization or approval decisions.
4. Only deterministic backend policy and authorization code may permit writes.
5. Approved writes must be bound to the exact actor, tenant, resource, action, arguments, evidence version and policy version.
6. Every write must revalidate authorization, approval and resource state immediately before execution.
7. Use idempotency keys and transactional safety for write actions.
8. Protect against prompt injection, cross-tenant access, replay and duplicate execution.
9. Enforce maximum agent steps, tool timeouts, token/cost budgets and cancellation.
10. Do not give the agent shell execution, arbitrary code execution, unrestricted HTTP fetch or an unrestricted database tool.
11. Use synthetic data only. Never commit secrets.
12. Use the deterministic mock provider by default. Real LLM use must remain optional.
13. Do not claim tests passed unless the commands actually ran successfully.
14. Do not claim production readiness from mock tests alone.
15. Do not push to GitHub or deploy without explicit instruction.

## Implementation practices

- Build maintainable, modular code with typed contracts.
- Add automated tests for every significant behavior.
- Prefer clear Python code over unnecessary agent frameworks.
- Use migrations for database schema changes.
- Make local startup reproducible.
- Maintain `.env.example`, `README.md` and documentation.
- Maintain a project architecture and decision log.
- Never silently bypass failures or weaken security checks to make tests pass.
- Avoid overengineering where simpler reliable implementations work.

## Phase execution

Implement only the phase requested. Do not skip ahead into later phases except for essential foundational interfaces.

Phase 13A is explicitly authorized in this separate publication snapshot: sanitize source, prepare accurate portfolio documentation and run local verification. Preserve the private original repository unchanged. No push, publication, deployment, external artifact upload or original history rewrite. Phase 12 remains PARTIAL. Initialize fresh Git only after the publication content audit passes; commit only with an explicitly approved public identity. Licensing choices require owner approval.

At the end of every phase, use the report template and return:

1. What was implemented.
2. Files created and modified.
3. Architecture decisions.
4. Commands actually executed.
5. Test results and failures.
6. Security and reliability concerns.
7. Remaining limitations.
8. Git status and commit hash if committed.
9. A clear verdict: **PASS**, **PARTIAL** or **BLOCKED**.

## Approved publication decisions

The owner approved MIT for original project code and the public Git author name Zohaib Hyder. The owner explicitly approved the public Git email 250129637+zohaib-hyder@users.noreply.github.com for author and committer and authorized ONE initial local commit after the final staged audit. Use repository-local identity only; never inherit workstation identity. No push, repository creation, publication or deployment.
