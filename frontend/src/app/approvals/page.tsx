"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Approval } from "@/lib/execution";
export default function ApprovalsPage() {
  const [items,setItems]=useState<Approval[]>([]); const [error,setError]=useState("");
  useEffect(()=>{ const controller=new AbortController(); api<{items:Approval[]}>("/approvals?limit=50",{signal:controller.signal}).then(r=>setItems(r.items)).catch(()=>{if(!controller.signal.aborted)setError("Unable to load approval queue");});return()=>controller.abort();},[]);
  return <><p className="eyebrow">PHASE 8 · SEPARATION OF DUTIES</p><h1>Approvals</h1><p>Review current evidence independently. A requester cannot approve their own action.</p>{error&&<p role="alert">{error}</p>}<section className="panel"><h2>Approval queue</h2>{!items.length&&!error&&<p>No approval requests available.</p>}{items.map(a=><article key={a.approval_id} className="border-b border-slate-700 py-4"><Link className="break-all underline" href={`/action-proposals/approval/${a.approval_id}`}>{a.proposal_id}</Link><p>{a.status} · expires {new Date(a.expires_at).toLocaleString()}</p></article>)}</section></>;
}
