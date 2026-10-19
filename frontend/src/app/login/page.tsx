"use client";
import { FormEvent, Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
function LoginForm() {
  const { login, loading, error: sessionError } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const params = useSearchParams();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      setPassword("");
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to sign in");
      setPassword("");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main id="main" className="login-page">
      <section className="login-intro">
        <span className="brand-icon">N</span>
        <p className="eyebrow">NORTHSTAR CONTROLLED OPERATIONS</p>
        <h1>
          Trusted access.
          <br />
          Clear boundaries.
        </h1>
        <p>
          Sign in to your synthetic tenant workspace. Every data request is
          scoped to your server-validated identity.
        </p>
        <span className="phase-pill">
          Phase 1 · Authentication & access control
        </span>
      </section>
      <section className="login-card">
        <p className="eyebrow">SYNTHETIC ENVIRONMENT</p>
        <h2>Sign in to Northstar</h2>
        <p className="muted">
          Use the fictional identity and password configured locally.
        </p>
        {params.get("reason") === "session-expired" && (
          <p className="notice" role="status">
            Your session has expired or was revoked. Sign in again.
          </p>
        )}
        <form onSubmit={submit}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            required
            maxLength={200}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            maxLength={256}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {(error || sessionError) && (
            <p className="error-message" role="alert">
              {error || sessionError}
            </p>
          )}
          <button className="button" type="submit" disabled={busy || loading}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <small>
          No real customer systems. Credentials are never stored in browser
          storage. Agent execution is not yet implemented.
        </small>
      </section>
    </main>
  );
}
export default function LoginPage() {
  return (
    <Suspense fallback={<main role="status">Loading sign in…</main>}>
      <LoginForm />
    </Suspense>
  );
}
