"use client";
import Link from "next/link";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "./auth-provider";
import { Sidebar } from "./sidebar";
import { permittedPath } from "@/lib/navigation";
export function Shell({ children }: { children: React.ReactNode }) {
  const { user, loading, error, expired, refresh } = useAuth();
  const path = usePathname();
  const router = useRouter();
  useEffect(() => {
    if (!loading && !error && !user && path !== "/login")
      router.replace(expired ? "/login?reason=session-expired" : "/login");
    if (!loading && user && path === "/login") router.replace("/");
  }, [user, loading, error, expired, path, router]);
  if (path === "/login") return children;
  if (loading)
    return (
      <main className="auth-status" role="status">
        Checking your session…
      </main>
    );
  if (error)
    return (
      <main className="auth-status">
        <h1>Service unavailable</h1>
        <p role="alert">{error}</p>
        <button className="button" onClick={() => void refresh()}>
          Try again
        </button>
      </main>
    );
  if (!user)
    return (
      <main className="auth-status" role="status">
        Redirecting to sign in…
      </main>
    );
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="workspace">
        <header className="topbar">
          <span>
            Northstar Services{" "}
            <span className="muted">/ Authenticated workspace</span>
          </span>
          <span className="badge">
            {user.role.toUpperCase()} · SYNTHETIC DATA
          </span>
        </header>
        <main id="main" key={`${user.session_id}:${user.role}`}>
          {permittedPath(path, user.permissions) ? (
            children
          ) : (
            <section className="placeholder">
              <h1>Access denied</h1>
              <p>
                Your role does not grant access to this area. Backend
                permissions remain authoritative.
              </p>
              <Link className="button" href="/">
                Back to overview
              </Link>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
