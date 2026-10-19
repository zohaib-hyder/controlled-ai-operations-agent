# Phase 13A — sanitized publication snapshot

## Scope and current decision

**Current source-audit decision: READY_FOR_PUBLICATION_REVIEW; exact staged-tree and post-commit checks must also pass.** Earlier license/identity statements below record the initial preparation state; the owner decision follow-up at the end supersedes them. Phase 12 remains **PARTIAL**, with 16 unique unresolved High CVEs across local image/vendor-SBOM profiles. No source push, publication or deployment is authorized. The private original remains unchanged; only this separate snapshot is edited.

## Implementation and files

Copied tracked application source, tests, migrations, locks, Compose/Dockerfiles, synthetic fixtures and relevant architecture/security/evaluation documentation. Excluded Git history, local credentials/dependencies/builds/logs/caches and seven old screenshot binaries. COPY_AUDIT.json records the copy and sanitized file list. README now presents current behavior and exact limitations; historical phase reports remain historical, with private paths/commit references removed. Portfolio case study, seven Mermaid diagrams, demo, LinkedIn/Upwork drafts, publication checklist, license inventory, contribution and disclosure guidance were created. Package-maintainer contacts in the OS inventory were omitted without removing package/version or vulnerability evidence.

## Decisions

Separate source snapshot rather than rewriting private history. Keep security findings visible. Distinguish historical private-baseline measurements from new copy checks. Keep mock default, agent limits, tenant/approval/write/fencing contracts unchanged. Give the publication Compose stack a distinct project/volume name; ports still require isolation. Defer project license and public commit identity to explicit owner approval. No Git initialization before content audit; no commit with inherited private identity.

## Verification

New copy checks completed below; historical full-suite counts are not attributed to this snapshot. Local scans use no remote service. Raw development reports are excluded from publication.

## Security and remaining limitations

Publication blockers include owner license/identity choices and incomplete verification. Native and cross-platform dependency notice review is incomplete. No live LLM, real enterprise writes, production deployment or accepted container release. Historical npm-audit metadata transmission/possible aborted-build telemetry remains disclosed. No new external scanner upload is authorized.

## Git

No original Git metadata copied. No new Git repository/commit yet; no public identity approved. No remote/push/history rewrite. Final integrity checks and decision will be appended.

## Executed verification and outcomes

All commands targeted this publication snapshot. Existing locked Python/Node dependencies were reused as read-only tooling; no dependency directory, private virtualenv or original Git metadata was copied. The backend import path and running mounted source hash were checked against this copy. The isolated project `northstar-publication13a` used 55434/38000/33000 and a newly generated local credential; no original database was used.

- Original readonly Git checks: HEAD, clean porcelain status, `rev-list --count --all` (15), snapshot tree hash; repeated at final integrity audit.
- `python3 scripts/publication_checks.py --output artifacts/publication-audit.json`: local pattern/identity/credential review and local Markdown target checks; final source-only result recorded in PUBLICATION_AUDIT.json. External URLs not fetched; fragment anchors not validated.
- Copy-root toolchain Ruff `check --no-cache --config backend/pyproject.toml backend scripts` and `format --check --no-cache`: PASS; 135 Python files.
- From backend, `TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55434/northstar_publication_test APP_ENV=test AI_PROVIDER=mock python -m pytest -q tests/test_publication_checks.py tests/test_release_tooling.py tests/test_image_scan_tooling.py tests/test_data.py tests/test_authentication_pool.py tests/test_system.py -o cache_dir=../artifacts/pytest-cache`: **41 passed**, one upstream warning, 6.47 seconds. Earlier 37-test run passed before adding health checks and a fixture-string assembly adjustment.
- `docker run --rm --pull never --network none --cpus 2 --memory 2g --mount type=bind,src=<publication-root>/frontend,dst=/workspace,readonly --entrypoint /bin/sh controlled-ai-operations-frontend-checks:phase12 -c 'cp -R /workspace/. /app/ && rm -rf /app/.next && node --version && npm run lint && npm run typecheck && npm test && npm run build'`: **PASS**, Node 26.12.0, 50 Vitest tests in nine files, fresh production build. Uses installed dependencies from a local image; no upload/download or inherited source result substituted for the copied source.
- `docker compose -p northstar-publication13a -f docker-compose.yml -f artifacts/publication.compose.yml config --quiet`: PASS. New-volume DB startup, publication-mounted `alembic upgrade head`, `python -m app.db.seed_auth`, and `up -d --no-build --wait backend frontend worker`: PASS. Runtime images reuse local preexisting dependencies; no new image release certification is claimed.
- `DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55434/northstar APP_ENV=development AI_PROVIDER=mock python scripts/prepare_release_browser.py --confirm-synthetic-local`: fresh fictional records in publication DB only.
- Local Playwright CLI with ignored custom port/config and capture hooks around copied `release-e2e/workflow.spec.ts`: **one unique desktop business workflow passed** (10.6 seconds), zero failed/skipped/flaky cases, retries zero. Actual independent approval, worker completion, verified receipt, idempotency/replay and foreign-tenant denials. A string `grep` configuration failed before test execution; corrected to RegExp, raw failure retained locally. This is not 64 fresh cases.
- Local authenticated read-only queue recapture after data loaded: PASS. Eight actual screens visually reviewed, PNG text/EXIF chunks absent. Incident screenshot is empty-state only; no incident-detail capture claimed.
- Live health/readiness and frontend: **200/200/200**; JSON parsing and backend source binding passed.

No fresh full 727-test suite, 601-scenario catalog, 64-case browser suite, performance cohort, restart coordinator or image scans were run. Those historical results retain their scope. No runtime authority/agent budget/schema change was made. See [reviewed verification](../portfolio/VERIFICATION.json) and [screenshots](../portfolio/SCREENSHOTS.md).

## Initial publication decision (superseded by owner follow-up)

**BLOCKED** pending owner license/public identity, incomplete platform/native notices/provenance review. No new Git repository or commit is created while these gates remain open. Git preflight found author/committer would resolve from unapproved workstation fallback; no explicit user.name/user.email or identity environment overrides were configured. Values were not printed or copied. License and identity questions were sent for owner input; lack of a reply is not approval.

Phase 12 remains **PARTIAL** with 16 unique unresolved High CVEs. This is a source-publication review, not container release acceptance. Nothing pushed, published, deployed or externally scanned; no paid/live LLM call. Historical npm-audit/possible telemetry exception remains disclosed. The copy's temporary credential, database and raw verification logs are development artifacts excluded from the final source snapshot; final cleanup/integrity outcomes are recorded below.

## Initial cleanup and integrity

The task-created publication Compose containers/network/disposable volume were removed after checks. The newly generated local `.env` credential was deleted. Raw verification artifacts were moved to an operator-local temporary directory outside the publication source tree; redacted reviewed summaries and actual screenshots remain here. No dependency directory, cache, image archive, dump or runtime log remains in this source copy.

Original HEAD, 15-commit count, clean working tree and tracked-tree checksum were rechecked against the initial record and matched. Original Git remotes/history/files were not modified. Publication has no `.git`, author/committer metadata, commit, remote or inherited parent history. Public identity and license approval remain required. **Final decision: BLOCKED; Phase 12 PARTIAL unchanged.**

Final audit tooling was tightened to exact reviewed synthetic credential matches (including a hash-bound provider fixture), rather than exempting a test directory. Seven audit guard tests passed in 0.04 seconds after that change, including a synthetic-looking unknown test credential that must still block. Six overlap the earlier 41-test run; these counts are not added as independent suites. Gitleaks/TruffleHog were not installed; this is a reproducible local pattern/fixture audit with explicit limitations, not independent forensic certification. Standard container runtime paths and documented disposable `/tmp` paths remain; private workstation paths and hostnames do not.

## Owner-approved MIT and public-name follow-up

The owner explicitly approved MIT for original project code and the public author name Zohaib Hyder. Created LICENSE using that public name without an email, THIRD_PARTY_NOTICES.md, PUBLIC_IDENTITY.json and LOCAL_LICENSE_REVIEW.json. Updated README, contribution/checklist/license review, AGENTS and verification metadata. No application, API, dependency version, schema, agent budget, execution or tenant boundary changed.

Read available upstream license texts locally for the previously incomplete Python labels and Psycopg/binary; retained relative file identifiers/hashes, not contact data. Source-only review found no known restricted vendored code/assets. Platform-native redistribution notices remain a future container/binary distribution gate, not a claim that every third-party artifact was legally qualified. No such artifacts are shipped in this snapshot. This is not independent legal/provenance certification.

No exact public email has been approved. No Git initialization, local Git identity configuration, commit, push, repository creation, deployment, publication or external source/metadata upload was performed. The approved author name does not authorize inheriting a private email. Phase 12 remains PARTIAL with 16 unique unresolved High CVEs and the historical external-transmission exception disclosed. **Current source-publication decision: BLOCKED pending exact public-email approval.**

Follow-up checks and original integrity are recorded in VERIFICATION.json and PUBLICATION_AUDIT.json. Earlier 41 focused backend tests, 7 overlapping final audit guards, 50 Vitest tests, production build and one desktop browser workflow retain their original scope/date; no fresh full-suite rerun is implied by a documentation/license update.

Owner-decision follow-up actually executed: local upstream-license inspection/hash inventory; `python3 scripts/publication_checks.py --output docs/portfolio/PUBLICATION_AUDIT.json` (369 files, 160 local targets, zero blocking matches/broken targets; 17 external links not fetched); `python -m pytest -q backend/tests/test_publication_checks.py -o cache_dir=/tmp/northstar-publication-pytest-cache` (7 passed, 0.04 seconds); Ruff check and format check (135 files, PASS); JSON parse (40 files); original HEAD/tree/15 commits/clean status and publication no-Git/no-credential checks (PASS). No full backend/frontend/browser rerun was needed for this documentation/license-only follow-up. Public email remains absent, and no commit was created.

## Exact public identity approval and initial-commit preparation

The owner explicitly approved Zohaib Hyder and the exact public noreply email recorded in PUBLIC_IDENTITY.json for author and committer. Initialized a fresh empty `main` repository with an empty template; no original Git metadata was copied. Configured repository-local user.name/user.email and user.useConfigOnly. Effective author/committer match; no identity/config environment override, active include/includeIf directive, hook/signing override, remote or existing HEAD was found. No private values were printed or inherited.

Updated the scanner to allow only the exact owner-approved public address, with a regression guard rejecting another noreply address. This is an explicit public-identity exception, not an exemption for arbitrary personal emails. Older email-pending and uncommitted decisions above are historical. Phase 12 remains PARTIAL, including 16 unresolved unique High CVEs and the documented earlier external-transmission exception. This preparation authorizes only one local initial commit after audit; no push, repository creation, publication or deployment.

The committed report records pre-commit evidence; the resulting commit hash/root count/author/committer/file count/clean tree are checked and reported after commit so no self-referential hash or unperformed post-commit claim is embedded.

## Final approved-identity source audit (pre-commit record)

Executed local content/link audit: 369 candidate files, zero blocking pattern matches, 160 valid local targets, 17 external URLs deliberately not fetched. Nine publication audit guards passed in 0.06 seconds, including exact approved noreply acceptance and rejection of an unapproved noreply address. Ruff and format checks passed (135 Python files). Fifteen Git exclusion probes confirmed credentials, nested environment files, dependencies/builds, raw artifacts, keys, dumps, archives and logs remain ignored; five safe source/example/lock paths remain eligible. Full runtime suites were not rerun for this identity/documentation/audit-tool update; earlier tested source-copy results remain scoped separately.

MIT, separate third-party notice handling, README, seven Mermaid diagrams, case study, demo guide, LinkedIn/Upwork drafts and eight real reviewed screenshots are present. Screenshot hashes/PNG metadata are checked against the reviewed inventory. No publication blocker remains in this bounded source audit. Existing native/container licensing qualification and Phase 12 PARTIAL with 16 High CVEs remain separate future release gates; the historical transmission exception is preserved.

Next local steps authorized by the owner: inspect and validate all staged paths/bytes against this source inventory, check staged whitespace/secret/identity exclusions, create exactly one initial commit with the approved message, then verify root-only history, both identities, file count, clean tree and original integrity. The resulting commit hash is reported after execution; this pre-commit document does not claim those later commands already ran. No push/publication/repository creation/deployment or external upload is authorized.
