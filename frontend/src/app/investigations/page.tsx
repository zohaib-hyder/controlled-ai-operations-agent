"use client";
import { FormEvent, useEffect, useState, useRef } from "react";
import Link from "next/link";
import { InvestigationDisplay } from "@/components/investigation-result";
import { InvestigationHistory } from "@/components/investigation-history";
import { api, ApiError } from "@/lib/api";
import { investigationBody, InvestigationResult } from "@/lib/investigations";
interface Item {
  id: string;
  name?: string;
  customer_id?: string;
  account_id?: string;
  subject?: string;
}
export default function InvestigationWorkspace() {
  const [customers, setCustomers] = useState<Item[]>([]),
    [accounts, setAccounts] = useState<Item[]>([]),
    [tickets, setTickets] = useState<Item[]>([]);
  const [customer, setCustomer] = useState(""),
    [ticket, setTicket] = useState(""),
    [goal, setGoal] = useState("");
  const [result, setResult] = useState<InvestigationResult | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    const c = new AbortController();
    Promise.all([
      api<{ items: Item[] }>("/customers?limit=100", { signal: c.signal }),
      api<{ items: Item[] }>("/accounts?limit=100", { signal: c.signal }),
      api<{ items: Item[] }>("/tickets?limit=100", { signal: c.signal }),
    ])
      .then(([cs, ac, ts]) => {
        setCustomers(cs.items);
        setAccounts(ac.items);
        setTickets(ts.items);
      })
      .catch(() => {
        if (!c.signal.aborted)
          setError("Unable to load investigation resources. Reload to retry.");
      })
      .finally(() => {
        if (!c.signal.aborted) setLoading(false);
      });
    return () => c.abort();
  }, []);
  const allowedAccounts = new Set(
    accounts.filter((a) => a.customer_id === customer).map((a) => a.id),
  );
  const creationKey = useRef<{ payload: string; key: string } | null>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResult(null);
    let body;
    try {
      body = investigationBody(goal, customer, ticket);
    } catch (e) {
      setError((e as Error).message);
      return;
    }
    const payload = JSON.stringify(body);
    if (creationKey.current?.payload !== payload)
      creationKey.current = { payload, key: crypto.randomUUID() };
    setBusy(true);
    try {
      setResult(
        await api<InvestigationResult>("/investigations", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Idempotency-Key": creationKey.current.key,
          },
          body: payload,
        }),
      );
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : "Investigation unavailable. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <p className="eyebrow">PHASE 4 · DURABLE INVESTIGATION</p>
      <h1>Investigation Workspace</h1>
      <p className="page-description">
        Deterministic mock planning with authorized tools. Recommendations are
        advisory; account eligibility and writes are not implemented.
      </p>
      <section className="tool-detail" aria-label="New investigation">
        <h2>New investigation</h2>
        {loading && <p role="status">Loading authorized resources…</p>}
        <form onSubmit={submit} className="tool-form">
          <label>
            Customer
            <select
              aria-label="Customer"
              value={customer}
              onChange={(e) => {
                setCustomer(e.target.value);
                setTicket("");
              }}
              disabled={busy || loading}
              required
            >
              <option value="">Select customer</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Ticket (optional)
            <select
              aria-label="Ticket (optional)"
              value={ticket}
              onChange={(e) => setTicket(e.target.value)}
              disabled={busy || !customer}
            >
              <option value="">Use first ticket in stable order</option>
              {tickets
                .filter((t) => allowedAccounts.has(t.account_id || ""))
                .map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.subject}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Investigation goal
            <textarea
              aria-label="Investigation goal"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              minLength={5}
              maxLength={1000}
              rows={3}
              required
              disabled={busy}
            />
          </label>
          <button
            className="button"
            disabled={busy || loading || !customers.length}
          >
            {busy
              ? "Awaiting bounded backend result…"
              : "Run read-only investigation"}
          </button>
        </form>
      </section>
      {error && (
        <p role="alert" className="error-banner">
          {error}
        </p>
      )}
      {result && (
        <>
          <Link
            className="button"
            href={`/investigations/${result.investigation_id}`}
          >
            Open persistent investigation detail
          </Link>
          <InvestigationDisplay result={result} />
        </>
      )}
      <InvestigationHistory refreshToken={result?.investigation_id || ""} />
      <p className="page-description">
        Results, checkpoints and execution history are stored in PostgreSQL.
        Recommendations remain advisory; no business write or approval execution
        is available.
      </p>
    </>
  );
}
