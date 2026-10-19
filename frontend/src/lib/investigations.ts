export interface SourceEvidence {
  evidence_id: string; source_type: string; source_resource_id: string;
  source_reference: string; source_version: number | null;
  source_updated_at: string | null; collected_at: string;
  freshness: "CURRENT" | "STALE" | "UNKNOWN"; historical: boolean;
  summary: string; facts: Record<string, unknown>;
  retrieval_metadata: Record<string, unknown>;
}
export const terminalStates = [
  "COMPLETED",
  "NEEDS_REVIEW",
  "FAILED",
  "CANCELLED",
  "BUDGET_EXCEEDED",
];
export interface InvestigationResult {
  iteration_count?: number;
  execution_limits?: { max_steps: number; max_tool_calls: number; planning_iterations: number; wall_seconds: number; provider_requests: number; provider_output_tokens: number; provider_cost_microusd: number } | null;
  tool_selection_trace?: { iteration: number; decision_type: string; summary: string; selected_tool: string | null; arguments_hash: string | null; step_id: string | null; tool_execution_id: string | null; observation_id: string | null; evidence_ids: string[]; validation_outcome: string; budget_consumption: Record<string, number>; stop_reason: string | null; timestamp: string }[];
  version: number;
  customer_id: string;
  ticket_id: string | null;
  created_at: string;
  updated_at: string;
  checkpoint_sequence: number;
  checkpoint_valid: boolean;
  recovery_attempts: number;
  cancel_requested: boolean;
  lease_expires_at: string | null;
  recovery_available: boolean;
  planner_type: string;
  planner_version: string;
  budget_counters: {
    provider_requests?: number;
    provider_output_tokens_reserved?: number;
    provider_cost_microusd_reserved?: number;
    no_progress?: number;
    tool_calls: number;
    planning_iterations: number;
    observation_bytes: number;
    elapsed_ms: number;
  };
  investigation_id: string;
  goal: string;
  status: string;
  history: string[];
  steps: {
    step_id: string;
    invocation: {
      tool_name: string;
      tool_version: string;
      arguments: Record<string, unknown>;
    };
    purpose: string;
    status: string;
  }[];
  reconciliation?: {
    conflicts: { conflict_id: string; conflict_type: string; evidence_ids: string[]; severity: string; explanation: string; required_follow_up: string }[];
    gaps: { gap_id: string; kind: string; explanation: string }[];
    grounded_findings: { kind: string; text: string; evidence_ids: string[] }[];
  } | null;
  evidence: {
    sources?: SourceEvidence[];
    evidence_id: string;
    tool_execution_id: string;
    tool_name: string;
    tool_version: string;
    source_reference: string;
    source_references: string[];
    summary: string;
    collected_at: string;
    validation_status: string;
  }[];
  findings: { text: string; evidence_ids: string[] }[];
  recommended_next_steps: string[];
  uncertainty: string[];
  stop_reason: string;
  tool_calls_performed: number;
  duration_ms: number;
  human_review_recommended: boolean;
  correlation_id: string;
}
export function investigationBody(
  goal: string,
  customer_id: string,
  ticket_id: string,
) {
  if (goal.trim().length < 5 || goal.length > 1000)
    throw new Error("Goal must contain 5–1000 characters.");
  if (
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
      customer_id,
    )
  )
    throw new Error("Select a customer.");
  return {
    goal: goal.trim(),
    customer_id,
    ...(ticket_id ? { ticket_id } : {}),
  };
}
