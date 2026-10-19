# 0008 — Evaluation-only policy decisions

The Phase 7 PDP uses the existing live session authorization, creator-scoped investigation repository, canonical persisted evidence and tenant-constrained ORM records. It is separate from the six read-only tools and does not duplicate their execution path. Search ranking, policy descriptions and planner prose are untrusted data.

A static Python action catalog and strict schemas define proposal eligibility. Current structured policy rules are accepted only in explicitly supported shapes. Overlapping effective versions are ambiguous and denied, rather than silently selecting the greatest version. Historical expired versions remain available for audit.

Proposals, immutable decision receipts and correlated audit events commit together. Revalidation appends a receipt; it never rewrites history. Current status is computed from resource, policy, evidence and actor bindings. ALLOW is eligibility only. There are no approval grants, execution permissions or business mutation endpoints.

Application-level append-only protection does not protect against a privileged database administrator. PostgreSQL RLS and cryptographic external audit storage remain outside this phase.

Docker imports application code directly from `/app` after installing all frozen locked dependencies with `--no-install-project`. An additional editable packaging step was redundant and timed out resolving an isolated setuptools build environment. Removing that step does not skip dependency verification or runtime checks and avoids a second package-index request after source copy.
