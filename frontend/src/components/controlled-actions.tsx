"use client";
import Link from "next/link";
import { useState } from "react";
import { useAuth } from "./auth-provider";
import { api } from "@/lib/api";
import { Approval, controlled, executionKey, ExecutionResult } from "@/lib/execution";

export function ExecutionView({ result }: { result: ExecutionResult }) {
  return <section className="panel" aria-live="polite"><h2>Execution: {result.status}</h2><p>Outcome verified: {result.verified && result.status === "COMMITTED" ? "Yes" : "No"}</p>{result.replayed && <p>Existing result returned; no second mutation.</p>}{result.error_code && <p role="alert">{result.error_code}</p>}{result.status === "UNCERTAIN" && <p>Do not submit a new request. Reconcile with the same idempotency key when storage returns.</p>}<div className="grid min-w-0 gap-4 md:grid-cols-2"><div className="min-w-0"><h3>Before</h3><pre className="overflow-x-auto text-xs">{JSON.stringify(result.before || {}, null, 2)}</pre></div><div className="min-w-0"><h3>After</h3><pre className="overflow-x-auto text-xs">{JSON.stringify(result.after || {}, null, 2)}</pre></div></div><h3>Audit timeline</h3>{result.events?.map(e => <p key={e.type}>{e.type} · {new Date(e.created_at).toLocaleString()}</p>)}{!result.events && <p>Committed receipts include a correlated audit timeline.</p>}</section>;
}
export function ControlledActions({ proposal, decision, status }: { proposal: string; decision: string; status: string }) {
  const { user } = useAuth();
  const [approval, setApproval] = useState<Approval | null>(null);
  const [result, setResult] = useState<ExecutionResult | null>(null);
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  async function act(requestApproval: boolean) {
    if (!user) return; setBusy(true); setError("");
    try { if (requestApproval) setApproval(await controlled<Approval>(`/action-proposals/${proposal}/approval-requests`, {}));
      else {
        let value = await controlled<ExecutionResult>(`/action-proposals/${proposal}/execute`, { decision_id: decision }, executionKey(user.user_id, proposal));
        if (value.execution_id) value = await api<ExecutionResult>(`/action-executions/${value.execution_id}`);
        setResult(value);
      }
    } catch (e) { setError(e instanceof Error ? e.message : "Operation failed"); } finally { setBusy(false); }
  }
  if (!user) return null;
  return <section className="panel"><h2>Controlled synthetic operation</h2><p>Execution revalidates identity, policy, evidence and versions. Restricted actions require a different reviewer.</p>{status === "APPROVAL REQUIRED" && !approval && <button disabled={busy} onClick={() => void act(true)} className="button">Request independent approval</button>}{status === "ALLOWED" && user.permissions.includes("action:execute") && <button disabled={busy} onClick={() => void act(false)} className="button">Execute synthetic action</button>}{approval && <p><Link href={`/action-proposals/approval/${approval.approval_id}`}>Approval: {approval.status}</Link></p>}{error && <p role="alert">{error}</p>}{result && <ExecutionView result={result} />}</section>;
}
