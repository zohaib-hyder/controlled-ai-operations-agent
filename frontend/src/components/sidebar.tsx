"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { visibleNavigation } from "@/lib/navigation";
import { useAuth } from "./auth-provider";
export function Sidebar() {
  const path = usePathname();
  const { user, logout } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function signOut() {
    setBusy(true);
    setError("");
    try {
      await logout();
    } catch {
      setError("Sign out failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <aside className="sidebar">
      <Link href="/" className="brand">
        <span className="brand-icon">N</span>
        <span>
          Northstar<small>CONTROLLED OPERATIONS</small>
        </span>
      </Link>
      <p className="nav-caption">WORKSPACE</p>
      <nav aria-label="Main navigation">
        {visibleNavigation(user?.permissions || []).map((item) => (
          <Link
            key={item.href}
            href={item.href}
            aria-current={path === item.href ? "page" : undefined}
            className={path === item.href ? "nav-link selected" : "nav-link"}
          >
            <span aria-hidden="true">{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="user-panel">
        <strong>{user?.role}</strong>
        <p>{user?.email}</p>
        <small>Tenant {user?.tenant_id.slice(0, 8)} · Synthetic</small>
        <button
          className="logout-button"
          disabled={busy}
          onClick={() => void signOut()}
        >
          {busy ? "Signing out…" : "Sign out"}
        </button>
        {error && <p role="alert">{error}</p>}
      </div>
    </aside>
  );
}
