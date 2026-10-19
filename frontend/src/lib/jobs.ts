export type Job = {
  id: string; proposal_id: string; actor_id: string; action_name: string;
  action_version: string; status: string; attempt_count: number; max_attempts: number;
  next_run_at: string; created_at: string; updated_at: string; lease_expires_at: string | null;
  receipt_id: string | null; last_error: string | null; age_seconds: number;
  can_cancel: boolean; can_retry: boolean;
};
export type JobEvent = {state: string; category: string; correlation_id: string; created_at: string};
export function recoveryMessage(status: string) {
  if (status === "RECONCILIATION_REQUIRED") return "Outcome needs evidence reconciliation. No blind retry.";
  if (status === "DEAD_LETTERED") return "Retry budget exhausted. Authorized retry must pass current security checks.";
  if (status === "COMPLETED") return "Completed with a verified execution receipt.";
  if (status === "RUNNING") return "Execution in progress. Cancellation cannot promise rollback.";
  return status.replaceAll("_", " ");
}
