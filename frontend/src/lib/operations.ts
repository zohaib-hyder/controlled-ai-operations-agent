export type Range = {range:string;start?:string;end?:string};
export function rangeQuery(window:Range) {const q=new URLSearchParams({range:window.range});if(window.range==="custom"){q.set("start",window.start || "");q.set("end",window.end || "");}return q.toString();}
export type Rate={numerator:number;denominator:number;percent:number|null};
export type Summary={count:number;mean_seconds:number|null;p50_seconds:number|null;p95_seconds:number|null};
export type Activity={id:string;timestamp:string;event_type:string;source:string;entity_id:string;actor_id:string|null;service:string;correlation_id:string|null;summary:string};
export type Thresholds={dead_letter_backlog:number;reconciliation_backlog:number;queue_age_seconds:number;worker_stale_seconds:number;failure_percent:number;failure_min_samples:number};
export type Overview={start:string;end:string;snapshot_at:string;scope:string;metrics:{investigation_counts:Record<string,number>;job_counts:Record<string,number>;investigation_completion:Rate;job_success:Rate;retry_rate:Rate;dead_letter_rate:Rate;approval_rejection:Rate;investigation_duration:Summary;approval_turnaround:Summary;execution_latency:Summary;volume:{day:string;investigations:number;retries:number}[];pending_approvals:number;expiring_approvals:number;open_incidents:number;queue_depth:number;oldest_queue_age_seconds:number|null;reconciliation_backlog:number;dead_letter_backlog:number;lease_expirations:number};health:Record<string,string>;alerts:{code:string;severity:string;message:string}[];thresholds:Thresholds;recent:Activity[]};
export type Incident={id:string;category:string;status:string;severity:string;title:string;description:string;assigned_to:string|null;job_id:string|null;approval_id:string|null;created_at:string;resolution_note:string|null;can_respond:boolean};
export type IncidentDetail={incident:Incident;events:{id:string;event_type:string;status:string;note:string|null;created_at:string;actor_id:string|null;correlation_id:string}[]};
export type Trace={links:{kind:string;id:string;href:string}[];timeline:Activity[];truncated:boolean};
export function percent(r:Rate){return r.percent===null?"No samples":`${r.percent.toFixed(1)}% (${r.numerator}/${r.denominator})`;}
export function canRespond(role:string){return role==="admin"||role==="reviewer";}
