import { expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import ActionProposals from "../app/action-proposals/page";

it("labels eligibility as evaluation only and provides no execute control", () => {
  const html = renderToStaticMarkup(<ActionProposals />);
  expect(html).toContain("ALLOW means policy eligibility");
  expect(html).toContain("No business action is executed");
  expect(html).toContain("Evaluate eligibility");
  expect(html).not.toMatch(/>Execute</);
});
it("requires explicit investigation, target and canonical evidence", () => {
  const html = renderToStaticMarkup(<ActionProposals />);
  expect(html).toContain('name="investigation"');
  expect(html).toContain('name="target"');
  expect(html).toContain('name="evidence"');
  expect(html).not.toContain('name="tenant_id"');
  expect(html).not.toContain('name="actor_id"');
});

import { currentDecisionStatus } from "./action-status";
it("expires an allowed receipt at the inclusive expiry boundary", () => {
  expect(currentDecisionStatus("ALLOWED", "2026-01-01T00:00:00Z", Date.parse("2026-01-01T00:00:00Z"))).toBe("STALE");
});
it("expires approval eligibility and rejects invalid expiry timestamps", () => {
  expect(currentDecisionStatus("APPROVAL REQUIRED", "2026-01-01T00:00:00Z", Date.parse("2026-01-02T00:00:00Z"))).toBe("STALE");
  expect(currentDecisionStatus("ALLOWED", "invalid", 0)).toBe("STALE");
});
it("retains a backend stale decision even before its expiry", () => {
  expect(currentDecisionStatus("STALE", "2026-01-02T00:00:00Z", Date.parse("2026-01-01T00:00:00Z"))).toBe("STALE");
});

import { canReview, executionKey } from "./execution";
import { ExecutionView } from "../components/controlled-actions";
it("requires explicit approval permission and a different reviewer", () => {
  expect(canReview(["action:approve"], "reviewer", "operator", "PENDING")).toBe(true);
  expect(canReview(["action:approve"], "operator", "operator", "PENDING")).toBe(false);
  expect(canReview([], "reviewer", "operator", "PENDING")).toBe(false);
  expect(canReview(["action:approve"], "reviewer", "operator", "INVALIDATED")).toBe(false);
});
it("keeps the execution key stable across operator retries", () => {
  expect(executionKey("actor", "proposal")).toBe(executionKey("actor", "proposal"));
  expect(executionKey("other", "proposal")).not.toBe(executionKey("actor", "proposal"));
});
it("renders verified before and after state and replay information", () => {
  const html=renderToStaticMarkup(<ExecutionView result={{status:"COMMITTED",verified:true,replayed:true,before:{status:"blocked"},after:{status:"active"}}}/>);
  expect(html).toContain("COMMITTED"); expect(html).toContain("blocked"); expect(html).toContain("active"); expect(html).toContain("no second mutation");
});
it("does not present an uncertain execution as verified", () => {
  const html=renderToStaticMarkup(<ExecutionView result={{status:"UNCERTAIN",verified:false,error_code:"execution_outcome_uncertain"}}/>);
  expect(html).toContain("same idempotency key"); expect(html).not.toContain("Outcome verified: Yes");
});
