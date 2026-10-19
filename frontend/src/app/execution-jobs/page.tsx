"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Job, JobEvent, recoveryMessage } from "@/lib/jobs";
import { executionKey, ExecutionResult } from "@/lib/execution";
import { ExecutionView } from "@/components/controlled-actions";
import { useAuth } from "@/components/auth-provider";

type Queue = {items: Job[]; queue_depth: number; oldest_age_seconds: number};
export default function JobsPage() {
  const { user } = useAuth();
  const [queue, setQueue] = useState<Queue | null>(null);
  const [selected, setSelected] = useState<Job | null>(null);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [attempts, setAttempts] = useState<{number:number;outcome:string;error_category:string|null}[]>([]);
  const [receipt, setReceipt] = useState<ExecutionResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [proposal, setProposal] = useState("");
  const [decision, setDecision] = useState("");
  const [approval, setApproval] = useState("");
  async function refresh() { setQueue(await api<Queue>("/execution-jobs")); }
  useEffect(() => { let live = true; api<Queue>("/execution-jobs").then(q => { if(live) setQueue(q); }).catch(e => {if(live) setError(e.message);}); return () => {live=false;}; }, []);
  async function inspect(id: string) {
    setBusy(true); setError(""); setReceipt(null);
    try {
      const [job, timeline, history] = await Promise.all([api<Job>(`/execution-jobs/${id}`),api<{items:JobEvent[]}>(`/execution-jobs/${id}/events`),api<{items:typeof attempts}>(`/execution-jobs/${id}/attempts`)]);
      setSelected(job); setEvents(timeline.items); setAttempts(history.items);
      if(job.receipt_id) setReceipt(await api<ExecutionResult>(`/action-executions/${job.receipt_id}`));
    } catch(e) {setError(e instanceof Error ? e.message : "Job unavailable");} finally {setBusy(false);}
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault(); if(!user) return; setBusy(true);setError("");
    try {
      const job = await api<Job>("/execution-jobs",{method:"POST",headers:{"Idempotency-Key":executionKey(user.user_id,proposal)},body:JSON.stringify({proposal_id:proposal,decision_id:decision,approval_id:approval || null})});
      await refresh(); await inspect(job.id);
    } catch(e) {setError(e instanceof Error ? e.message : "Submission failed");} finally {setBusy(false);}
  }
  async function control(operation: string) {
    if(!selected) return;setBusy(true);setError("");
    try {await api(`/execution-jobs/${selected.id}/${operation}`,{method:"POST",body:"{}"});await refresh();await inspect(selected.id);}
    catch(e){setError(e instanceof Error ? e.message : "Operation failed");}finally{setBusy(false);}
  }
  return <div className="space-y-6"><header><p className="eyebrow">Controlled operations</p><h1>Execution jobs</h1><p>Durable synthetic work. Submission does not authorize future execution.</p></header>
    {error && <p role="alert">{error}</p>}
    <section className="panel"><h2>Queue visibility</h2><p>Active jobs: {queue?.queue_depth ?? "Loading"} · Oldest age: {queue ? Math.round(queue.oldest_age_seconds)+"s" : "Loading"}</p><button className="button" disabled={busy} onClick={()=>void refresh().catch(e=>setError(e.message))}>Refresh jobs</button></section>
    {user?.permissions.includes("action:execute") && <form className="panel space-y-3" onSubmit={submit}><h2>Queue an evaluated proposal</h2><p>Use an existing proposal and its exact decision ID. Restricted actions need an approved request.</p><label className="block">Proposal ID<input className="block w-full" value={proposal} onChange={e=>setProposal(e.target.value)} required /></label><label className="block">Decision ID<input className="block w-full" value={decision} onChange={e=>setDecision(e.target.value)} required /></label><label className="block">Approval ID (when required)<input className="block w-full" value={approval} onChange={e=>setApproval(e.target.value)} /></label><button className="button" disabled={busy}>Submit durable job</button></form>}
    <section className="panel"><h2>Jobs</h2>{queue?.items.length === 0 && <p>No execution jobs.</p>}<div className="space-y-3">{queue?.items.map(j=><article key={j.id} className="rounded border border-slate-700 p-4"><button className="text-violet-300" onClick={()=>void inspect(j.id)} disabled={busy}>{j.action_name} · {j.status}</button><p className="break-all text-xs">{j.id}</p><p>Attempts {j.attempt_count}/{j.max_attempts} · Next run {new Date(j.next_run_at).toLocaleString()}</p><p>{j.last_error || "No error recorded"}</p></article>)}</div></section>
    {selected && <section className="panel space-y-3"><h2>Job: {selected.status}</h2><p>{recoveryMessage(selected.status)}</p>{selected.can_cancel && <button disabled={busy} className="button" onClick={()=>void control("cancel")}>Cancel job</button>}{selected.can_retry && <button disabled={busy} className="button" onClick={()=>void control("retry")}>Retry with revalidation</button>}<h3>Attempts</h3>{attempts.map(a=><p key={a.number}>Attempt {a.number}: {a.outcome} {a.error_category}</p>)}<h3>Job event timeline</h3>{events.map((event,i)=><p key={i}>{event.state} · {event.category} · {new Date(event.created_at).toLocaleString()}</p>)}</section>}
    {receipt && <ExecutionView result={receipt} />}
  </div>;
}
