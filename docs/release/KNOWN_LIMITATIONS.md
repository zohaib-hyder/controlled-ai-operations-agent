> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Known limitations and release blockers

- Local mock AI and synthetic PostgreSQL only. No paid/live LLM tests, real enterprise writes, hosted CI, deployment, independent security certification or production capacity evidence.
- The historical Phase 10 transient eligibility failure cause remains unconfirmed. A Phase 12 full run also had one `missing_policy` wall-clock termination (722 passed/one failed); five exact repeats passed. Its cause remains unconfirmed; later success does not erase it. Phase 11 repeated successful runs do not establish a root-cause fix. Default production agent wall budget remains eight seconds.
- Trusted-Origin CSRF defense assumes trusted same-origin app/proxy. No synchronizer token protocol exists; XSS/compromised trusted origins remain risks.
- ORM append-only controls do not stop a database owner. No RLS or immutable external audit retention is established.
- The standard worker is serial. Global four/per-tenant one admission caps do not prove strict fairness or no starvation for arbitrary loads.
- Read-only latency samples do not establish investigation, approval, tool, execution or queue throughput. p99 requires at least 100 samples; a single login is not an authentication latency distribution.
- A local queued-job restart is distinct from OS-kill-at-commit, ambiguous execution reconciliation, expired-lease and investigation recovery testing. Existing integration cases cover selected fault injection, not every real process-failure timing.
- Dependency findings and failed scans must be reviewed in DEPENDENCY_AUDIT. Removing tooling from images narrows installed surface; it does not certify all remaining components safe.
- Dedicated reset intentionally destroys marked demo history. It is not a migration rollback or backup mechanism. Never use it against the primary development database.
- Frontend production builds and responsive workflows do not establish a network transfer budget, large-timeline stress baseline or browser rendering performance profile. No such capacity claim is made.
- Every required Phase 12 verification gap remains an acceptance blocker until fresh evidence exists. The serial harness returns nonzero and PARTIAL while its explicit missing-evidence list is nonempty. No release-candidate acceptance is implied by passing individual checks.

- Offline scans are now complete, but backend/worker each retain 55 high matches with no listed distro fixed versions. Final frontend has three medium matches; the later Node 26 candidate resolves the observed static 3.5.8 copy, with a Current-channel lifecycle tradeoff. The vendor wheel assessment adds two High PCRE2 advisories beyond full-image package counts. See IMAGE_SECURITY for exact exposure/fix status; no severity suppression or implicit risk acceptance.
- The whole-task no-metadata-transmission objective was not fully met: early remediation npm auto-audit sent dependency metadata; anonymous build telemetry from an aborted attempt cannot be excluded. Defaults were corrected and final build/scan egress constrained. Image scans themselves uploaded nothing; this does not erase the earlier exception.

- Latest wheel does not mean all private native libraries are patched. Psycopg 3.3.6 includes mapped private crypto/PCRE2; vendor backport labels and SBOM matching do not prove exploitability or completeness. A supported system-libpq installation requires separate native-linking qualification; no manual `.so` substitution was performed.
- The official Node 26.12.0 container is Current rather than LTS. Local build/browser verification does not establish a production support policy; requalify a maintained LTS runtime when appropriate. No release criterion is changed by this runtime selection.

## Final runtime verification

Fresh full backend regression: **727 passed, zero failed/skipped, one upstream warning, 838.59 seconds**; evaluation catalog **601/601**, no measured critical failures/evidence gaps. Ruff/format passed (133 files). Under Node **26.12.0**, frontend lint/typecheck and **50 Vitest tests** passed; production Docker build, Compose configuration and Alembic drift check passed.

Final browser rerun: **64/64 passed** (52 default, four release, eight isolated negative), zero skipped/flaky cases, retries disabled. Before this final run both stacks were explicitly recreated and all six service image IDs matched the scanned digests. An earlier successful 64-case cohort is preserved separately because the old backend/worker image metadata could not be inspected. Runtime mappings were refreshed after recreation. Live health/readiness returned **200**. Restart recovery passed with durable snapshot preserved, queued job completed, one receipt/one business record and zero duplicate mutations. This is graceful queued-job restart evidence, not crash-at-commit proof. Full reviewed results: [RUNTIME_VERIFICATION.json](RUNTIME_VERIFICATION.json), [runtime inventory](RUNTIME_INVENTORY.json).

**PARTIAL:** no release-policy waiver exists for the 14 unique image High CVEs plus two additional native PCRE2 High advisories. New scans/build checks uploaded no project artifacts or metadata; historical npm-audit transmission and possible telemetry remain disclosed. No full coordinator, performance or clean-volume installation rerun is implied; those prior results retain their original scope. No push, deploy, publish, live LLM, production acceptance or Phase 13.
