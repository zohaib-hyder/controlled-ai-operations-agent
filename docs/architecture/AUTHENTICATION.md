> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Authentication

Phase 1 adds email/password authentication over opaque server-side sessions. This is a synthetic portfolio application, not a production certification.

## Login and session lifecycle

1. Browser submits JSON email/password through the same-origin Next.js `/api/v1` proxy. The proxy only forwards fixed route families to a server-configured backend, preserves Origin and never invents a trusted Origin. No CORS allowance is needed.
2. FastAPI rejects missing/untrusted Origin and cross-site Fetch Metadata on login/logout. Origin must exactly match `TRUSTED_ORIGINS`, including scheme and port. SameSite=Lax supplements this check; it does not replace it.
3. PostgreSQL-backed throttle buckets serialize per normalized email and backend-observed client address using transaction-scoped advisory locks. Five identity failures or 30 client failures in a five-minute window block further attempts with 429. Unknown identities use the same counters and generic failures. Forwarded IP headers are not trusted. Old throttle windows older than a day are opportunistically removed.
4. Email lookup is case-insensitive and globally unique. Argon2id uses 64 MiB memory, three iterations and parallelism two with random salts. Unknown/unprovisioned users verify against a process-generated dummy hash. Invalid, disabled and unknown identities receive the same 401 message. Hash parameters are upgraded on successful login when necessary.
5. Generate a 32-byte cryptographically random token via `secrets.token_urlsafe(32)`. Only its SHA-256 digest is stored. A session row binds the user and tenant using a composite foreign key. A successful login rotates/revokes a presented browser session, including when changing identities, and creates a fresh token. Other devices are not silently signed out.
6. Session creation/rotation and security audit events commit atomically before the cookie is returned. The cookie is host-only, HttpOnly, SameSite=Lax, Path=/, with explicit expiry/Max-Age. Default lifetime is one hour (maximum configurable lifetime one day).
7. Each protected request validates the token digest, expiry, revocation, user activity and current role in PostgreSQL. Identity contains user ID, tenant ID, role and session ID; these never come from browser claims. Password hashes and token digests are never API response fields.
8. Logout requires a trusted Origin plus a valid session, revokes that row, records logout/revocation and expires the cookie. Replaying the old token fails. Expired/revoked sessions receive a generic 401.

Authentication failure events commit even when the API returns a denial. Audit failure or database failure prevents successful authentication. Request validation errors do not echo submitted bodies. Request logs omit bodies, query strings, cookies and passwords. Security events contain no raw tokens or password material. `/auth/me` exposes the authenticated user's own email plus identity/permissions, not other users' details. All API/proxy responses disable caching.

## Environment and transport

Local HTTP is explicitly development-only: `APP_ENV=development`, `COOKIE_SECURE=false`, exact origins `http://localhost:3000` and `http://127.0.0.1:3000`. Published Compose ports bind loopback. This permits local browser testing without pretending HTTP cookies are transport-secure.

For an HTTPS environment set `APP_ENV=production`, `COOKIE_SECURE=true` and an explicit JSON list of HTTPS `TRUSTED_ORIGINS`. Production validation rejects insecure cookie/origin configuration and a nonempty `DEMO_PASSWORD`. Use trusted TLS termination and privately reachable backend/database infrastructure; deployment is not part of this phase. Do not source the JSON-bearing `.env` as a shell script. The internal backend address is server-only `BACKEND_INTERNAL_URL`; browsers always call their own origin.

## Synthetic credentials

Run `python3 scripts/create_demo_credentials.py` after copying `.env.example`. It generates a random password in ignored `.env`, sets file mode 0600 and never prints it. Existing local credentials are preserved. Open `.env` locally to retrieve your demo password. The explicit `python -m app.db.seed_auth` command enables only the deterministic eight fixture users. No demo password is committed or embedded in frontend source. Password salts are intentionally random; IDs and seed structure remain deterministic, and repeat seed runs preserve existing hashes and passwords.

Production seed refusal is enforced both by settings and by the seed service, independently of its environment argument. Ordinary business seeding does not activate logins. There is no registration, password reset, recovery, MFA or user-management endpoint in this phase.

## Limits

The backend-observed address behind the same-origin proxy is shared across browsers; the 30-failure cap can throttle that entire local workspace. A production edge rate limiter and explicit trusted-proxy design remain future work. Account-based throttles can also be abused for temporary denial of access. Argon2 work is bounded per verification but has not been load-tested at production concurrency. Session rows are retained after expiry/revocation; automated retention is not implemented. The UI refreshes sessions on focus and responds to protected-API 401s; the backend enforces expiry even if an idle page has stale presentation state. Credential changes/global device revocation and administrative user provisioning require future interfaces.

Design references: [OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [OWASP CSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html), [argon2-cffi API](https://argon2-cffi.readthedocs.io/en/stable/api.html).
