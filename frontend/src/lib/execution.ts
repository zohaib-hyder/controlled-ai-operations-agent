export interface ExecutionResult {
  status: "COMMITTED" | "FAILED" | "DENIED" | "UNCERTAIN";
  execution_id?: string; verified: boolean; error_code?: string; replayed?: boolean;
  before?: Record<string, unknown>; after?: Record<string, unknown>; idempotency_key?: string;
  events?: { type: string; correlation_id: string; created_at: string }[];
}
export interface Approval {
  approval_id: string; proposal_id: string; decision_id: string; requested_by: string;
  reviewer_id?: string; status: string; consumed: boolean; expires_at: string;
  action_name: string; target_resource_id: string; error_code?: string;
  receipt: { reason_codes: string[]; evidence_references: string[]; policy_versions: { key: string; version: number }[] };
  sources?: { evidence_id: string; summary: string; facts: Record<string, unknown> }[];
  decisions: { status: string; reason: string; actor_id: string; created_at: string }[];
}
export function executionKey(actor: string, proposal: string) { return `ui-${actor}-${proposal}`; }
export async function controlled<T>(path: string, body: unknown, key?: string): Promise<T> {
  const response = await fetch(`/api/v1${path}`, { method: "POST", credentials: "same-origin", cache: "no-store", headers: { "Content-Type": "application/json", ...(key ? { "Idempotency-Key": key } : {}) }, body: JSON.stringify(body) });
  const data = await response.json();
  if (response.status === 401) window.dispatchEvent(new Event("session-expired"));
  if (!response.ok && !data.status) throw new Error(data.error?.message || "Controlled operation failed");
  return data as T;
}
export function canReview(permissions: string[], actor: string, requester: string, status: string) {
  return permissions.includes("action:approve") && actor !== requester && status === "PENDING";
}
