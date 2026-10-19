import { expect, test } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { InvestigationDisplay } from "@/components/investigation-result";
import type { InvestigationResult } from "@/lib/investigations";

test("source inspection uses escaped facts, freshness and evidence anchors", () => {
  const result = {
    investigation_id: "synthetic", status: "NEEDS_REVIEW", duration_ms: 1,
    tool_calls_performed: 1, history: [], steps: [], findings: [],
    recommended_next_steps: [], uncertainty: [], human_review_recommended: true,
    evidence: [{ evidence_id: "envelope", tool_name: "get_ticket", source_references: [],
      sources: [{ evidence_id: "source", source_type: "ticket", freshness: "UNKNOWN",
        historical: false, summary: "<script>untrusted</script>", source_reference: "ticket:synthetic",
        source_updated_at: null, facts: { status: "open" }, retrieval_metadata: {} }] }],
    reconciliation: { conflicts: [], gaps: [{ gap_id: "gap", explanation: "Missing policy" }],
      grounded_findings: [{ kind: "observed_fact", text: "Ticket open", evidence_ids: ["source"] }] },
  } as unknown as InvestigationResult;
  const html = renderToStaticMarkup(<InvestigationDisplay result={result} />);
  expect(html).toContain('id="evidence-source"');
  expect(html).toContain('href="#evidence-source"');
  expect(html).toContain("UNKNOWN");
  expect(html).toContain("Missing policy");
  expect(html).not.toContain("<script>");
  expect(html).toContain("&lt;script&gt;");
  expect(html).toContain("grants no action permission");
});

test("planner trace labels actual mode and links an executed observation", () => {
  const result = {
    investigation_id: "synthetic", status: "NEEDS_REVIEW", duration_ms: 1,
    tool_calls_performed: 1, history: [], steps: [], findings: [], evidence: [],
    recommended_next_steps: [], uncertainty: [], human_review_recommended: true,
    planner_type: "openai_compatible", planner_version: "2.0", iteration_count: 2,
    budget_counters: { provider_requests: 1, provider_output_tokens_reserved: 1024, provider_cost_microusd_reserved: 5000 },
    tool_selection_trace: [{ iteration: 2, decision_type: "CALL_TOOL", summary: "Executed read", selected_tool: "search_policy", validation_outcome: "executed", evidence_ids: [], observation_id: "observation-id", timestamp: "2026-10-17T00:00:00Z" }],
  } as unknown as InvestigationResult;
  const html = renderToStaticMarkup(<InvestigationDisplay result={result} />);
  expect(html).toContain("Optional real LLM");
  expect(html).toContain("Reservations are budget bounds, not billed usage");
  expect(html).toContain('href="#observation-observation-id"');
  expect(html).toContain("Human review required");
  expect(html).not.toContain("confidence");
});
