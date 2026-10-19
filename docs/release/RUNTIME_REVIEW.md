> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 12 runtime exposure review

Baseline: `private-baseline`. Synthetic local systems and mock AI only. No change to release criteria, approval authority, authentication, tenant isolation, execution fencing or database schema.

## Why 110 high matches are not 110 vulnerabilities

The backend and worker each have 55 high package/advisory matches. Their entire 166-row vulnerability inventories are identical after excluding image identity. Together the high rows represent **14 distinct CVEs and 21 distinct installed package/version pairs**. Nine util-linux binary packages can inherit one source-package advisory, and both service images repeat that inventory. This explains duplication without suppressing a single finding.

The complete machine inventory is [RUNTIME_HIGH_FINDINGS.json](RUNTIME_HIGH_FINDINGS.json); it preserves each advisory, binary package/version, image, fix state and separately downloaded Debian maintainer status. The original/final CSV inventories retain every severity. The downloaded public Debian feed SHA256 is recorded in the machine inventory. Debian's issue-priority/deferral language is not used to downgrade Grype's severity.

## Runtime inventory and actual dependencies

Full package/command inventory and exact main/isolated running-image binding are committed in [RUNTIME_INVENTORY.json](RUNTIME_INVENTORY.json). Image-only probes ran with networking disabled. Process-library observations came from `/proc/1/maps` inside the actual backend and worker; these show mappings, not function-call traces. Loaded does not mean the vulnerable function was exercised; absent from one snapshot does not prove impossible future loading.

| Component | Backend / worker | Frontend |
| --- | --- | --- |
| Required language runtime | Python 3.12.15, FastAPI, SQLAlchemy/Psycopg | Node serving Next standalone output |
| Node/npm/npx | All absent; Node is not a backend/worker dependency | Node required; npm/npx absent from runtime |
| Yarn/Corepack/pnpm shims | Absent | Found unused in baseline; removed in this follow-up |
| Compilers/build tools | gcc/g++/cc/make, uv, pip absent from runtime | gcc/g++/cc/make absent; TypeScript/lint/test tooling remains build-only |
| Package management | apt/apt-get/dpkg retained from supported Debian base, not used by service entrypoint | apk retained for supported Alpine image maintenance; no JS package manager needed |
| Shared OpenSSL | System OpenSSL 3.5.7-1~deb13u3 and vendored Psycopg crypto libraries actually mapped | Alpine libcrypto/libssl 3.5.9-r0 retained/patched for OS tools; Node does not dynamically link them |
| Native runtime libraries | libc, zlib, libgcc/libstdc++, libuuid and native Python/wheel dependencies mapped | musl, libgcc/libstdc++ plus packaged native Next/image dependencies |
| Development dependencies | Locked runtime environment excludes pytest/Ruff/build tooling | Standalone runtime excludes ESLint, TypeScript, Vitest and full build tree |

A package named `gcc-14-base` is not evidence of an installed compiler. `libgcc`/`libstdc++` are actual runtime libraries. Deleting their files, the package database or essential Debian packages to lower counts would conceal risk or break compatibility; none was done. apt/dpkg/apk are retained deliberately rather than manually dismantling a supported base. They are never exposed as agent tools.

## Supported runtime alternatives and decision

Public release metadata was retrieved with ordinary GET requests to `nodejs.org`, `pypi.org` and Debian's complete public security feed; no repository manifest or inventory was submitted. A separate official Python base container, containing no application files/mounts, downloaded public Debian package indexes to inspect candidates.

| Option | Evidence | Decision |
| --- | --- | --- |
| Node 24.22.0 LTS | Official release index reports bundled OpenSSL 3.5.8 | Kept as historical baseline; changing Alpine's shared OpenSSL cannot replace its static crypto |
| Node 22.23.3 LTS | Official release index also reports OpenSSL 3.5.8 | Downgrade would not resolve this component concern |
| Node 26.12.0 Current | Official maintained release reports bundled OpenSSL 3.5.9; same Alpine 3.24 base available | Candidate production build succeeded with no network; final runtime probe verified 3.5.9. Adoption requires the regression results below. Current-channel tradeoff is explicit; this is not an LTS production recommendation |
| Python 3.12.15 slim Trixie | Installed libc/zlib/OpenSSL already equal apt's current candidates | Retain existing tested ABI; no applicable stable package update was available |
| Python 3.12.15 slim Bookworm | Official supported tag; all corresponding high source-family advisories remain open in Debian's feed | No demonstrated patched alternative justifies a distribution downgrade; not installed/adopted |
| Python 3.12.15 Alpine | Official supported tag, but changes glibc→musl and native wheel selection | Requires separate ABI/driver qualification; not adopted solely to lower scanner counts |

Sources: [Node release inventory](https://nodejs.org/dist/index.json), [Node release lifecycle](https://nodejs.org/en/about/previous-releases), [Node 26.12.0 release](https://nodejs.org/en/blog/release/v26.12.0), [official Python variants](https://hub.docker.com/_/python), [Debian security feed](https://security-tracker.debian.org/tracker/data/json). No custom cryptographic compilation, mixed unstable Debian packages or arbitrary upstream patches were applied.

## Bundled native libraries require separate assessment

Psycopg and psycopg-binary are already **3.3.6**, also the latest public versions observed in PyPI metadata. An automatic dependency update would therefore not resolve the observed bundle. The actual service maps include both wheel-provided libcrypto families. Calling their version-reporting functions locally returned **OpenSSL 3.5.8** and **OpenSSL 1.1.1k FIPS**. The wheel's installed `auditwheel.cdx.json` identifies the older copy as **AlmaLinux openssl-libs 1.1.1k-17.el8_6**; that vendor package identity is more precise than the upstream version label alone.

Neither a FIPS label nor a vendor version proves all fixes are present. Conversely, vendor backports mean an upstream version string alone cannot establish every applicable CVE. The vendor SBOM is assessed locally with the same egress-disabled Grype tool; it is never uploaded. Its findings are separate from the full-image matching results to avoid changing denominators or hiding inventory gaps.

A supported alternative is Psycopg's native/system-libpq installation, linking distro-managed libraries, rather than bundled binary wheels. That changes native linking, libpq/LDAP/Kerberos behavior, local installation requirements and update ownership; it is not an automatic patch to this tested image. No custom crypto build or untested database-driver replacement is applied. This remains an explicitly unresolved native-component/provenance concern. The local Compose database connection does not establish TLS/LDAP/GSS exposure testing for future enterprise systems.

## Release gate

Unfixed is not harmless; severity is not proof of exploitability. Existing release policy permits documented noncritical limitations but contains no explicit acceptance of these unresolved high native-library findings. No waiver, allowlist, suppression, changed threshold or claim of zero required vulnerabilities was introduced. The default eight-second agent wall budget is unchanged. The expected decision remains **PARTIAL**, subject to actual final verification; no local RC or production readiness is implied.

Historical npm-audit metadata transmission and possible aborted-build telemetry remain disclosed in IMAGE_SECURITY. This investigation does not claim historical zero transmission. All new application/SBOM scans have networking disabled; package downloads and public metadata GETs are separated from scanning. Docker Scout is not used.

## Per-advisory exposure matrix

Severity remains **High for every row**. Installed binary packages/versions and both image match counts are retained in the linked JSON/CSV. Confidence is high for installed-package identity, lower for a source-family match proving the vulnerable function exists in each binary, and unproven for remote exploitability.

| Advisory | Component / observed loading | Attack precondition | Fix and residual |
| --- | --- | --- | --- |
| CVE-2025-69720 | ncurses infocmp analyze_string: infocmp installed; no process execution in agent tool registry | Attacker-controlled input processed by infocmp; binary/source-family mapping is broader than the vulnerable function | No listed stable distro fix; retained unresolved High. |
| CVE-2026-102010 | libstdc++ priority queue erase_if: libstdc++ mapped; library function use not established | Trigger affected priority-queue erase/reallocation path | No listed stable distro fix; retained unresolved High. |
| CVE-2026-19499 | glibc strfmon/strfmon_l: libc mapped; no explicit app monetary-format API call found | Particular right-justified monetary formatting into a small caller buffer | No listed stable distro fix; retained unresolved High. |
| CVE-2026-5435 | glibc DNS diagnostic printing: libc and libresolv mapped in services; function calls not traced | TSIG diagnostic-print path must use an insufficient caller buffer | No listed stable distro fix; retained unresolved High. |
| CVE-2026-54369 | libacl pathname functions: libacl installed; not mapped in observed service snapshots | Privileged ACL caller processes attacker-controlled symlink path | No listed stable distro fix; retained unresolved High. |
| CVE-2026-54370 | ACL recursive walk TOCTOU: libacl installed; no explicit app ACL traversal | Privileged recursive ACL/path walk races a local pathname replacement | No listed stable distro fix; retained unresolved High. |
| CVE-2026-76642 | util-linux mount post-hooks: mount installed; libuuid mapped does not prove vulnerable mount code present in every matched library | Privileged mount helper failure and configured post-mount hooks | No listed stable distro fix; retained unresolved High. |
| CVE-2026-78408 | util-linux nsenter cgroup descriptor: nsenter installed; not called by agent; nonroot services | Privileged namespace entry with join-cgroup and inherited descriptor | No listed stable distro fix; retained unresolved High. |
| CVE-2026-78409 | util-linux mount subdir path resolution: mount installed; no privileged mode or SYS_ADMIN granted | Local control of pathname components in an authorized fstab subdir mount | No listed stable distro fix; retained unresolved High. |
| CVE-2026-78410 | util-linux restricted bind mount: mount installed; no agent shell; source-family matches span other packages | Local source-path replacement plus authorized bind/ownership mount behavior | No listed stable distro fix; retained unresolved High. |
| CVE-2026-82560 | Perl POD formatter: Perl installed; not mapped/invoked by the Python service snapshot | Crafted nested POD must reach Pod::Text formatting | No listed stable distro fix; retained unresolved High. |
| CVE-2026-85091 | zlib nonblocking gz write/format: libz mapped; no explicit gzprintf/gzvprintf calls; affected-range ambiguity retained | Nonblocking write stall followed by affected gz formatting/state path | No listed stable distro fix; retained unresolved High. |
| CVE-2026-9538 | Perl Archive::Tar: Perl installed; no agent shell/archive-Perl tool | Crafted archive size must reach the Perl tar reader | No listed stable distro fix; retained unresolved High. |
| CVE-2026-95619 | libstdc++ aligned operator new: libstdc++ and libgcc mapped; compiler executable absent | Large aligned allocation reaching vulnerable integer-overflow path | No listed stable distro fix; retained unresolved High. |

## Additional vendor-SBOM findings

The local wheel-SBOM scan, with **AlmaLinux 8 explicitly declared from its RPM provenance**, reported **two High, two Medium and one Low** match, zero ignored matches. This is a separate profile; the running images are still Debian and their image scans were not reclassified as AlmaLinux. Full results: [VENDOR_SBOM_REVIEW.json](VENDOR_SBOM_REVIEW.json). No SBOM was uploaded.

| Additional High advisory | Component and mapping | Attack preconditions | Available fix / residual |
| --- | --- | --- | --- |
| CVE-2026-86145 | Bundled pcre2 10.32-3.el8_6; libpcre2 mapped in both services | A crafted pattern reaches affected DFA workspace reuse, with the relevant heap-limit/state conditions | AlmaLinux fix 10.32-4.el8_10 exists. It cannot be installed over the private hashed wheel library using Debian apt. No proven app path to the function, but High remains unresolved. |
| CVE-2026-103111 | Same bundled PCRE2 component, also mapped | Attacker-controlled regular expressions reach affected JIT interfaces | Same vendor fix exists; current PyPI wheel is already 3.3.6. A vendor wheel refresh or a separately qualified system-libpq installation is required. No manual `.so` substitution or unsupported backport is applied. |

The two medium PCRE2 advisories, CVE-2026-89157 and CVE-2026-89158, describe 32-bit conditions; the images are arm64. Their severities remain in the unsuppressed vendor report rather than being deleted. Low CVE-2022-41409 also remains. No explicit application PCRE2/JIT calls were found; Python `re` is a different engine. Native LDAP/Kerberos/PQ paths and hostile database-server behavior were not exhaustively traced. Loaded-library observations are not proof of direct HTTP reachability or safety.

Across both profiles there are **16 unique High CVEs**: 14 in the identical backend/worker image inventories, plus two additional PCRE2 advisories surfaced by the installed vendor SBOM. Keep the 55-per-image scanner counts and the separate two-match SBOM result distinct; do not inflate them into distinct exploit counts or conceal the inventory gap. This additional evidence reinforces the PARTIAL decision.

## Final runtime verification

Fresh full backend regression: **727 passed, zero failed/skipped, one upstream warning, 838.59 seconds**; evaluation catalog **601/601**, no measured critical failures/evidence gaps. Ruff/format passed (133 files). Under Node **26.12.0**, frontend lint/typecheck and **50 Vitest tests** passed; production Docker build, Compose configuration and Alembic drift check passed.

Final browser rerun: **64/64 passed** (52 default, four release, eight isolated negative), zero skipped/flaky cases, retries disabled. Before this final run both stacks were explicitly recreated and all six service image IDs matched the scanned digests. An earlier successful 64-case cohort is preserved separately because the old backend/worker image metadata could not be inspected. Runtime mappings were refreshed after recreation. Live health/readiness returned **200**. Restart recovery passed with durable snapshot preserved, queued job completed, one receipt/one business record and zero duplicate mutations. This is graceful queued-job restart evidence, not crash-at-commit proof. Full reviewed results: [RUNTIME_VERIFICATION.json](RUNTIME_VERIFICATION.json), [runtime inventory](RUNTIME_INVENTORY.json).

**PARTIAL:** no release-policy waiver exists for the 14 unique image High CVEs plus two additional native PCRE2 High advisories. New scans/build checks uploaded no project artifacts or metadata; historical npm-audit transmission and possible telemetry remain disclosed. No full coordinator, performance or clean-volume installation rerun is implied; those prior results retain their original scope. No push, deploy, publish, live LLM, production acceptance or Phase 13.
