# Third-party dependency and asset notices

The root [MIT License](LICENSE) covers owner-authored project material. It does not relicense third-party dependencies, their native libraries, trademarks, system fonts or upstream notices.

This source snapshot contains imports and dependency lock metadata, not vendored dependency source, node_modules, wheels, native libraries, downloaded fonts or container archives. Installation downloads dependencies under their own licenses; preserve their original license/copyright/NOTICE files. Do not replace those files with this project's MIT license.

The [dependency inventory](docs/portfolio/DEPENDENCY_LICENSES.json) records 38 Python packages and 500 npm lock entries, including optional platform variants. [Local license review](docs/portfolio/LOCAL_LICENSE_REVIEW.json) records inspected upstream files and hashes without copying contact metadata.

| Family / examples | Scope and handling |
| --- | --- |
| MIT / BSD / ISC / Apache / Python-PSF | Retain applicable upstream license, copyright, attribution and NOTICE terms when redistributing covered material. |
| MPL-2.0: certifi, axe-core, lightningcss families | Keep upstream licensing distinct; review applicable covered-file/source obligations for any later redistribution or modifications. |
| LGPL: Psycopg/binary, sharp/libvips platform artifacts | Native libraries retain their own terms. Exact linking, notices and source/relinking obligations require platform-specific review before any binary/container release. |
| CC-BY-4.0: caniuse-lite; CC0 assets/metadata | Review applicable attribution/license terms before distributing covered data or artifacts. |

No platform binary or container distribution is approved by this source preparation. Missing local optional-platform installations do not establish their redistribution compliance. The known native-library CVEs and Phase 12 PARTIAL verdict are separate, unchanged gates.

Repository diagrams are text sources; UI decoration uses project CSS/text. CSS names system Arial/Helvetica/sans-serif fonts without bundling font files. Eight reviewed screenshots show only this synthetic application's rendered UI; the project license does not grant rights to third-party marks or fonts. No old screenshot binaries or outside artwork were copied. This is a bounded engineering inventory, not a legal opinion or exhaustive independent authorship certification.
