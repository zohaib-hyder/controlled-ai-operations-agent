export type DecisionStatus = "ALLOWED" | "APPROVAL REQUIRED" | "DENIED" | "STALE";

// Presentation guard only. The backend remains the authority for current eligibility.
export function currentDecisionStatus(status: DecisionStatus, expiresAt: string, now: number): DecisionStatus {
  const expiry = Date.parse(expiresAt);
  return !Number.isFinite(expiry) || now >= expiry ? "STALE" : status;
}
