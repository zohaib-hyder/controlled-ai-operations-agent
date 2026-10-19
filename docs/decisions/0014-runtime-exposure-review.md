# 0014 — Runtime component verification and supported crypto update

Status: local-release implementation, contingent on regression evidence; no production approval.

Inventory package versions and actual process mappings separately from scanner severities. Debian source-package advisories fan out over binary packages and the identical backend/worker filesystem, so 110 High image matches represent 14 distinct CVEs. Supplement full-image matching with the installed vendor SBOM when native libraries are not cataloged. Keep the two additional PCRE2 High SBOM advisories and their source context visible; do not relabel the Debian images as AlmaLinux or merge denominators carelessly.

Use official Node 26.12.0 on the existing Alpine 3.24 family to replace the Node 24 static OpenSSL 3.5.8 copy with 3.5.9. Both build/runtime use the same pinned release tag; record immutable final image digests separately. Remove unused runtime Yarn/Corepack/pnpm shims in addition to npm/npx. Preserve all agent, authorization and execution contracts. Production build and actual browser workflows must succeed before keeping this candidate.

This chooses a supported Current release over existing LTS for the local synthetic demo, with its maintenance/compatibility tradeoff explicit. Official Node 22/24 release metadata still reports OpenSSL 3.5.8. Production use needs a maintained LTS qualification; no production recommendation is made. No custom crypto build is introduced. CI targets the verified Node release; hosted CI is not claimed to have run.

Retain the existing Python 3.12/Trixie ABI. Its installed libc/zlib/OpenSSL versions already match current stable apt candidates; Bookworm's corresponding source-family advisories remain open. A musl switch or manual removal of essential libraries would need native-dependency qualification, not just lower counts. Compilers and Python build tools are already absent. A vendor-wheel update/system-libpq installation remains a tracked option for Psycopg's private native libraries; no untested binary substitution is made.

Keep egress disabled for scans and Next build, disable automatic audit/telemetry, and separate ordinary public artifact/index GET requests from project-metadata uploads. Preserve the historical npm-audit/telemetry exception. Unresolved high/native-component findings keep the release PARTIAL under the existing criteria; do not add an implicit waiver or change thresholds to declare PASS.
