> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Deployment readiness boundary

No deployment, publishing or hosted CI run is authorized or claimed. The target is a local portfolio release candidate, conditional on all required acceptance evidence.

| Mode | Configuration | Boundary |
| --- | --- | --- |
| Development | `.env.example`, generated ignored password, loopback Compose | Synthetic records and HTTP only |
| Automated tests | dedicated `_test` DB, APP_ENV=test, mock provider | Destructive fixtures hold exclusive DB lock |
| Local demo | isolated `northstar_demo`, explicit marker, mock provider | No customer integration; reset affects only marked DB |
| Future production | APP_ENV=production, Secure cookies, explicit HTTPS origins, no demo password | Additional architecture, capacity and security work required |

See `.env.example` for DB, session, logging, provider and agent budgets. Worker limits are currently fixed in backend code: global 4, tenant 1, 30-second lease, bounded attempts. One stock worker processes one job at a time; caps are concurrency safety limits across processes, not measured throughput guarantees. Ordered due-time selection with locked admission does not establish strict round-robin fairness or starvation freedom.

Future production needs least privilege DB roles, external identity/session/credential operations, TLS and proxy validation, secret management, backups/restore drills, availability/capacity testing, dependency remediation, network/container hardening and independently reviewed operational controls. Optional LLM use requires explicit fixed HTTPS endpoint, key/model and positive cost rates; standard release checks use mock only. Mock-provider tests do not establish real-provider safety.
