"use client";
import { FormEvent, useEffect, useState } from "react";
import { currentDecisionStatus, DecisionStatus } from "@/lib/action-status";
import { ControlledActions } from "@/components/controlled-actions";
import { api } from "@/lib/api";

type Evaluation = {
  proposal: { proposal_id: string; action_name: string; target_resource_id: string; evidence_references: string[] };
  status: DecisionStatus;
  stale_reasons: string[];
  receipt: { decision_id: string; decision: string; reason_codes: string[]; rule_identifiers: string[]; policy_versions: { id: string; version: number; key: string }[]; expires_at: string; execution_authorized: boolean };
};
const actions = ["create_customer_note", "add_ticket_note", "request_account_reactivation", "reactivate_account", "close_duplicate_ticket", "override_security_block"];
export default function ActionProposals() {
  const [result, setResult] = useState<Evaluation | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [now, setNow] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setBusy(true);
    const data = new FormData(event.currentTarget);
    const name = String(data.get("action"));
    try {
      setResult(await api<Evaluation>("/action-proposals", { method: "POST", body: JSON.stringify({
        investigation_id: data.get("investigation"), action_name: name, action_version: "1.0",
        target_resource_id: data.get("target"), evidence_references: String(data.get("evidence")).split(/[\s,]+/).filter(Boolean),
        arguments: name.includes("note") ? { content: data.get("content") } : name === "close_duplicate_ticket" ? { duplicate_of_id: data.get("original") } : {},
        reason: "Operator requests evaluation of synthetic evidence",
      }) }));
    } catch (e) { setError(e instanceof Error ? e.message : "Evaluation failed"); }
    finally { setBusy(false); }
  }
  async function refresh(revalidate: boolean) {
    if (!result) return; setBusy(true); setError("");
    try { setResult(await api<Evaluation>(`/action-proposals/${result.proposal.proposal_id}${revalidate ? "/revalidate" : "/decision"}`, { method: revalidate ? "POST" : "GET" })); }
    catch (e) { setError(e instanceof Error ? e.message : "Revalidation failed"); }
    finally { setBusy(false); }
  }
  return <><header className="page-header"><p className="eyebrow">PHASE 8 · CONTROLLED SYNTHETIC OPERATIONS</p><h1>Action proposals</h1><p>ALLOW means policy eligibility. No business action is executed by evaluation. Execution requires an explicit controlled request.</p></header>
    <section className="panel"><h2>Evaluate an action</h2><p>Use canonical evidence IDs from a completed investigation. Missing or stale evidence is denied.</p>
      <form onSubmit={submit} className="space-y-4">
        <label className="block">Investigation ID<input className="block w-full rounded border border-slate-600 bg-slate-900 p-2" name="investigation" required /></label>
        <label className="block">Action<select className="block w-full rounded border border-slate-600 bg-slate-900 p-2" name="action">{actions.map(a => <option key={a}>{a}</option>)}</select></label>
        <label className="block">Target resource ID<input className="block w-full rounded border border-slate-600 bg-slate-900 p-2" name="target" required /></label>
        <label className="block">Evidence IDs, separated by commas<textarea className="block w-full rounded border border-slate-600 bg-slate-900 p-2" name="evidence" required maxLength={4000} /></label>
        <label className="block">Note content (note actions)<textarea className="block w-full rounded border border-slate-600 bg-slate-900 p-2" name="content" maxLength={500} /></label>
        <label className="block">Original ticket ID (duplicate closure)<input className="block w-full rounded border border-slate-600 bg-slate-900 p-2" name="original" /></label>
        <button disabled={busy} className="rounded bg-violet-700 px-4 py-2">{busy ? "Evaluating…" : "Evaluate eligibility"}</button>
      </form></section>
    {error && <p role="alert">{error}</p>}
    {result && <section className="panel" aria-live="polite"><h2>{currentDecisionStatus(result.status, result.receipt.expires_at, now)}</h2><p>{result.proposal.action_name}</p><p className="break-all">Target: {result.proposal.target_resource_id}</p><p>Decision expires: {new Date(result.receipt.expires_at).toLocaleString()}</p><h3>Rule explanations</h3><ul>{result.receipt.rule_identifiers.map(r => <li key={r}>{r.replaceAll("_", " ")}</li>)}</ul><h3>Reason codes</h3><p>{result.receipt.reason_codes.join(", ")}</p>{result.stale_reasons.length > 0 && <p>Revalidation required: {result.stale_reasons.join(", ")}</p>}<h3>Policy versions</h3>{result.receipt.policy_versions.length ? result.receipt.policy_versions.map(p => <p key={p.id}>{p.key} v{p.version}</p>) : <p>Static catalog rules; no policy record required.</p>}<h3>Supporting evidence</h3><ul>{result.proposal.evidence_references.map(id => <li className="break-all" key={id}>{id}</li>)}</ul><p>Execution authorized: No</p><button disabled={busy} onClick={() => void refresh(false)} className="mr-4 underline">Check current status</button><button disabled={busy} onClick={() => void refresh(true)} className="underline">Revalidate eligibility</button></section>}
    {result && <ControlledActions proposal={result.proposal.proposal_id} decision={result.receipt.decision_id} status={currentDecisionStatus(result.status, result.receipt.expires_at, now)} />}
  </>;
}
