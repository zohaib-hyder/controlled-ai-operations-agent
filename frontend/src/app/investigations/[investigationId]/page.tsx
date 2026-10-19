"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { InvestigationResult, terminalStates } from "@/lib/investigations";
import { InvestigationDisplay } from "@/components/investigation-result";
interface EventRow {
  sequence: number;
  event_type: string;
  created_at: string;
  data: Record<string, unknown>;
}
export default function InvestigationDetail() {
  const { investigationId } = useParams<{ investigationId: string }>();
  const [result, setResult] = useState<InvestigationResult | null>(null),
    [events, setEvents] = useState<EventRow[]>([]),
    [cursor, setCursor] = useState(0),
    [more, setMore] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const c = new AbortController();
    Promise.all([
      api<InvestigationResult>(`/investigations/${investigationId}`, {
        signal: c.signal,
      }),
      api<{ items: EventRow[]; next_after: number }>(
        `/investigations/${investigationId}/events?limit=100`,
        { signal: c.signal },
      ),
      api<{ items: { evidence: InvestigationResult["evidence"][number] }[] }>(
        `/investigations/${investigationId}/evidence?limit=100`,
        { signal: c.signal },
      ),
    ])
      .then(([r, e, ev]) => {
        setError("");
        setResult({ ...r, evidence: ev.items.map((v) => v.evidence) });
        setEvents(e.items);
        setCursor(e.next_after);
        setMore(e.items.length === 100);
      })
      .catch((e) => {
        if (!c.signal.aborted) {
          setResult(null);
          setError(
            e instanceof ApiError ? e.message : "Unable to load investigation.",
          );
        }
      });
    return () => c.abort();
  }, [investigationId, refresh]);
  async function control(action: "cancel" | "resume") {
    setBusy(true);
    setError("");
    try {
      await api(`/investigations/${investigationId}/${action}`, {
        method: "POST",
        body: "{}",
      });
      setRefresh((v) => v + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }
  async function loadEvents() {
    setBusy(true);
    try {
      const page = await api<{ items: EventRow[]; next_after: number }>(
        `/investigations/${investigationId}/events?limit=100&after=${cursor}`,
      );
      setEvents((old) => [...old, ...page.items]);
      setCursor(page.next_after);
      setMore(page.items.length === 100);
    } catch {
      setError("Unable to load more events.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <p className="eyebrow">PHASE 4 · PERSISTENT HISTORY</p>
      <h1>Investigation detail</h1>
      <Link href="/investigations">Back to Investigation Workspace</Link>
      {error && <p role="alert">{error}</p>}
      {!result && !error && (
        <p role="status">Loading persistent investigation…</p>
      )}
      {result && (
        <>
          <section className="tool-detail">
            <h2>Checkpoint and recovery</h2>
            <p>
              Version {result.version} · Checkpoint {result.checkpoint_sequence}{" "}
              ·{" "}
              {result.checkpoint_valid
                ? "Validated checkpoint"
                : "Checkpoint invalid — recovery will fail closed"}
            </p>
            <p>
              Planner: {result.planner_type} v{result.planner_version} ·
              Recovery attempts: {result.recovery_attempts}
            </p>
            <p>
              Cancellation requested: {result.cancel_requested ? "Yes" : "No"}
            </p>
            <p>Lease expiry: {result.lease_expires_at || "No active lease"}</p>
            <p>
              Budget usage: {result.budget_counters.tool_calls} tool calls,{" "}
              {result.budget_counters.planning_iterations} planning iterations,{" "}
              {result.budget_counters.observation_bytes} observation bytes.
            </p>
            <div className="history-controls">
              <button
                className="button"
                disabled={busy}
                onClick={() => setRefresh((v) => v + 1)}
              >
                Refresh investigation
              </button>
              {!terminalStates.includes(result.status) && (
                <button
                  className="button"
                  disabled={busy || result.cancel_requested}
                  onClick={() => control("cancel")}
                >
                  Request cancellation
                </button>
              )}
              {result.recovery_available && (
                <button
                  className="button"
                  disabled={busy}
                  onClick={() => control("resume")}
                >
                  Attempt safe recovery
                </button>
              )}
            </div>
            <p>
              Recovery never blindly replays an unfinished tool call. A recorded
              in-flight step requires human review. Budgets are preserved.
            </p>
          </section>
          <InvestigationDisplay result={result} />
          <section className="tool-detail">
            <h2>Persistent execution events</h2>
            <ol className="event-list">
              {events.map((e) => (
                <li key={e.sequence}>
                  <strong>
                    #{e.sequence} {e.event_type}
                  </strong>
                  <p>{e.created_at}</p>
                  <code>{JSON.stringify(e.data)}</code>
                </li>
              ))}
            </ol>
            {more && (
              <button className="button" disabled={busy} onClick={loadEvents}>
                Load more events
              </button>
            )}
          </section>
        </>
      )}
    </>
  );
}
