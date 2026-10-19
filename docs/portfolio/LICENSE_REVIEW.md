# License and asset review

**Project license: MIT, explicitly approved by the owner.** The root LICENSE uses the approved public name **Zohaib Hyder**, without an email address. No original-repository identity or Git metadata was reused. The license applies to owner-authored project material and does not override third-party terms.

## Current source-only scope

Reviewed the source snapshot, dependency manifests/locks, locally available upstream license files, CSS/font references, UI decoration, diagrams and the eight actual synthetic screenshots. No vendored dependency code, node_modules, wheels/native binaries, downloaded font, external icon pack or container archive is included. No known proprietary/restricted copied asset was identified. Owner approval supplies the project-license decision; this review does not independently certify authorship of every line or constitute legal advice.

The [inventory](DEPENDENCY_LICENSES.json) covers 38 Python packages and 500 npm lock entries, including optional platform entries. Declared families include permissive licenses, MPL, LGPL, Python/PSF and Creative Commons. Previously missing Python metadata expressions were supplemented by reading local upstream license texts for certifi, h11, httpx, pluggy, python-dotenv and SQLAlchemy; Psycopg/binary LGPL texts were also inspected. Hashes and recognized families are in [LOCAL_LICENSE_REVIEW.json](LOCAL_LICENSE_REVIEW.json). Upstream files were read locally, not copied, stripped of notices or relicensed.

## Distribution boundary and remaining limits

Colorama, greenlet, tzdata and optional npm platform artifacts are not all installed in the available toolchain. Their lock metadata is inventoried, but exact native/platform notice/source compliance remains unverified for future binary/container distribution. This copy does not distribute those artifacts; no blanket compatibility or container-license clearance is claimed. Any future redistribution requires its own review and explicit authorization. [THIRD_PARTY_NOTICES](../../THIRD_PARTY_NOTICES.md) records the handling boundary.

System font names are CSS fallback requests, not shipped font files. Diagrams are repository-native Mermaid. UI decoration is CSS/text. Reviewed screenshots contain fictional application content, no credentials and no PNG text/EXIF metadata. Third-party marks/fonts retain their owners' rights. GitHub Actions have not run from this copy; referencing actions is not a license audit of their runtime artifacts.

**MIT and exact public Git identity are owner-approved; final staged audit and commit verification remain required for publication review readiness.** MIT approval does not grant push/publication/deployment permission. Phase 12 stays PARTIAL, and future native/container notice review remains a separate gate.
