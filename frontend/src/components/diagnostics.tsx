"use client";
import Link from "next/link";
import {useState} from "react";
import {api} from "@/lib/api";
import {Trace,Range,rangeQuery} from "@/lib/operations";
import {TimeFilter,Timeline} from "@/components/operations";
export default function Diagnostics({initialId}:{initialId:string}){
 const [id,setId]=useState(initialId);const [range,setRange]=useState<Range>({range:"24h"});const [trace,setTrace]=useState<Trace|null>(null);const [error,setError]=useState("");const [busy,setBusy]=useState(false);
 async function search(e:React.FormEvent){e.preventDefault();setBusy(true);setError("");setTrace(null);try{setTrace(await api<Trace>(`/operations/correlations/${encodeURIComponent(id)}?${rangeQuery(range)}`));}catch(e){setError(e instanceof Error?e.message:"Trace unavailable");}finally{setBusy(false);}}
 return <div className="space-y-5"><h1>Correlation diagnostics</h1><p>Search an investigation, proposal, decision, approval, execution, job or recorded correlation UUID. Missing links are never inferred.</p><TimeFilter value={range} onChange={setRange}/><form className="panel space-y-3" onSubmit={search}><label className="block">Correlation or entity ID<input aria-label="Correlation or entity ID" className="block w-full" value={id} onChange={e=>setId(e.target.value)} required/></label><button className="button" disabled={busy}>Trace operations</button></form>{error&&<p role="alert">{error}</p>}{trace&&<><section className="panel"><h2>Related records</h2>{trace.links.map(l=><p key={l.kind+l.id} className="break-all"><Link className="text-violet-300" href={l.href}>{l.kind}: {l.id}</Link></p>)}{trace.truncated&&<p>Trace reached its bounded result cap. Narrow the time range.</p>}</section><section className="panel"><h2>End-to-end operational timeline</h2><Timeline items={trace.timeline}/></section></>}</div>;
}
