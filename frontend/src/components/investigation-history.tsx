"use client";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
interface Row {
  investigation_id: string;
  customer_id: string;
  goal: string;
  status: string;
  created_at: string;
  stop_reason: string | null;
}
export function InvestigationHistory({
  refreshToken = "",
}: {
  refreshToken?: string;
}) {
  const [rows, setRows] = useState<Row[]>([]),
    [status, setStatus] = useState(""),
    [customer, setCustomer] = useState(""),
    [filter, setFilter] = useState(""),
    [offset, setOffset] = useState(0),
    [total, setTotal] = useState(0),
    [error, setError] = useState(""),
    [loadedKey, setLoadedKey] = useState("");
  const requestKey = JSON.stringify([refreshToken, status, filter, offset]);
  const busy = loadedKey !== requestKey;
  useEffect(() => {
    const c = new AbortController();
    const query = new URLSearchParams({ limit: "20", offset: String(offset) });
    if (status) query.set("status", status);
    if (filter) query.set("customer_id", filter);
    api<{ items: Row[]; total: number }>(`/investigations?${query}`, {
      signal: c.signal,
    })
      .then((p) => {
        setError("");
        setRows(p.items);
        setTotal(p.total);
      })
      .catch(() => {
        if (!c.signal.aborted)
          setError("Unable to load investigation history.");
      })
      .finally(() => {
        if (!c.signal.aborted) setLoadedKey(requestKey);
      });
    return () => c.abort();
  }, [requestKey, status, filter, offset]);
  function search(e: FormEvent) {
    e.preventDefault();
    if (
      customer &&
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
        customer,
      )
    ) {
      setError("Customer reference must be a UUID.");
      return;
    }
    setOffset(0);
    setFilter(customer);
  }
  return (
    <section
      className="tool-detail investigation-history"
      aria-label="Investigation history"
    >
      <h2>Investigation history</h2>
      <p>Persistent records created by your actor in this tenant.</p>
      <form className="tool-form" onSubmit={search}>
        <label>
          Status filter
          <select
            aria-label="Status filter"
            value={status}
            onChange={(e) => {
              setOffset(0);
              setStatus(e.target.value);
            }}
          >
            <option value="">All states</option>
            {[
              "CREATED",
              "PLANNING",
              "RUNNING",
              "COMPLETED",
              "NEEDS_REVIEW",
              "FAILED",
              "CANCELLED",
              "BUDGET_EXCEEDED",
            ].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          Customer reference
          <input
            aria-label="Customer reference"
            value={customer}
            onChange={(e) => setCustomer(e.target.value)}
            placeholder="Customer UUID"
          />
        </label>
        <button className="button">Search history</button>
      </form>
      {busy && <p role="status">Loading history…</p>}
      {error && <p role="alert">{error}</p>}
      {!busy && !error && (
        <>
          <p>{total} persisted investigations</p>
          {rows.length === 0 && <p>No matching investigations.</p>}
          <ul className="history-list">
            {rows.map((r) => (
              <li key={r.investigation_id}>
                <Link href={`/investigations/${r.investigation_id}`}>
                  {r.goal}
                </Link>
                <p>
                  <strong>{r.status}</strong> ·{" "}
                  {new Date(r.created_at).toLocaleString()}
                </p>
                <p className="technical-id">
                  {r.investigation_id} · Customer {r.customer_id}
                </p>
              </li>
            ))}
          </ul>
          <div className="history-controls">
            <button
              className="button"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - 20))}
            >
              Previous history page
            </button>
            <button
              className="button"
              disabled={offset + 20 >= total || offset >= 10000}
              onClick={() => setOffset(offset + 20)}
            >
              Next history page
            </button>
          </div>
        </>
      )}
    </section>
  );
}
