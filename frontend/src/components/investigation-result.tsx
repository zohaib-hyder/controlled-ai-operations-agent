import { InvestigationResult, terminalStates } from "@/lib/investigations";
export function InvestigationDisplay({
  result,
}: {
  result: InvestigationResult;
}) {
  return (
    <section className="investigation-result" aria-label="Investigation result">
      <div className="tool-detail">
        <h2>Execution result</h2>
        <p>
          <strong>{result.status}</strong> · {result.duration_ms.toFixed(0)} ms
          · {result.tool_calls_performed} tool calls
        </p>
        <p>
          Stop reason: <code>{result.stop_reason}</code>
        </p>
        <p className="technical-id">
          Investigation ID: {result.investigation_id}
        </p>
        <p className="technical-id">Correlation ID: {result.correlation_id}</p>
        <p>Actual state history: {result.history.join(" → ")}</p>
        {terminalStates.includes(result.status) &&
          !["COMPLETED", "NEEDS_REVIEW"].includes(result.status) && (
            <p role="alert">
              Investigation stopped: {result.stop_reason}. Available evidence is
              preserved below.
            </p>
          )}
      </div>
      <section className="tool-detail" aria-label="Planner execution trace">
        <h2>Observation-driven planning</h2>
        <p>Planner mode: <strong>{result.planner_type === "openai_compatible" ? "Optional real LLM" : "Deterministic mock"}</strong> · v{result.planner_version ?? "legacy"}</p>
        <p>Planning iterations: {result.iteration_count ?? result.budget_counters?.planning_iterations ?? 0}{result.execution_limits ? ` / ${result.execution_limits.planning_iterations}` : ""} · Tool calls: {result.tool_calls_performed}{result.execution_limits ? ` / ${result.execution_limits.max_tool_calls}` : ""}</p>
        <p>Review status: {result.status === "NEEDS_REVIEW" ? "Human review required" : "Advisory investigation only"}. Stop reason: {result.stop_reason}</p>
        {result.planner_type === "openai_compatible" && <p>Provider requests: {result.budget_counters?.provider_requests ?? 0} · Reserved output tokens: {result.budget_counters?.provider_output_tokens_reserved ?? 0} · Reserved cost (micro-USD): {result.budget_counters?.provider_cost_microusd_reserved ?? 0}. Reservations are budget bounds, not billed usage.</p>}
        <p>Decision summaries describe validated selections. Source observations are verified retrievals; planner interpretations grant no operational authority.</p>
        {!result.tool_selection_trace?.length && <p>No selection trace is available for this unexecuted or historical investigation.</p>}
        <ol>{result.tool_selection_trace?.map((t, i) => <li key={i}>
          <strong>Iteration {t.iteration} · {t.decision_type}</strong> · {t.validation_outcome}
          <p>{t.summary}{t.selected_tool ? `: ${t.selected_tool}` : ""}</p>
          <p className="technical-id">{t.timestamp}{t.arguments_hash ? ` · Arguments SHA256: ${t.arguments_hash}` : ""}</p>
          {t.observation_id && <p><a href={`#observation-${t.observation_id}`}>Inspect decision observation</a></p>}
          {!!t.evidence_ids.length && <EvidenceLinks ids={t.evidence_ids} />}
          {t.stop_reason && <p>Stop: {t.stop_reason}</p>}
        </li>)}</ol>
      </section>
      <section className="tool-detail">
        <h2>Step timeline and tool calls</h2>
        <ol>
          {result.steps.map((s) => (
            <li key={s.step_id}>
              <strong>
                {s.invocation.tool_name} v{s.invocation.tool_version}
              </strong>{" "}
              — {s.status}
              <p>{s.purpose}</p>
              <code>{JSON.stringify(s.invocation.arguments)}</code>
            </li>
          ))}
        </ol>
      </section>
      <section className="tool-detail">
        <h2>Verified retrieval evidence</h2>
        <p>
          Schema validation and tenant-scoped retrieval establish provenance,
          not the truth of source text.
        </p>
        {result.evidence.length === 0 && <p>No evidence collected.</p>}
        {result.evidence.map((e) => (
          <article key={e.evidence_id} id={`observation-${e.evidence_id}`} className="evidence-item">
            <h3>{e.tool_name}</h3>
            <p>{e.summary}</p>
            {e.sources?.map((source) => (
              <section key={source.evidence_id} id={`evidence-${source.evidence_id}`} className="evidence-item">
                <h4>{source.source_type} · {source.freshness}</h4>
                <p>{source.summary}</p>
                <p>{source.historical ? "Historical evidence; age does not invalidate the recorded event." : "Operational observation; freshness describes source age at collection."}</p>
                <p className="technical-id">{source.source_reference}</p>
                <details>
                  <summary>Inspect source details</summary>
                  <p>Source timestamp: {source.source_updated_at ?? "Unknown"}</p>
                  <p>Collected: {source.collected_at}</p>
                  <p>Applicability suggestion: {String(source.retrieval_metadata.applicability_suggestion ?? "not evaluated")}; grants no action permission.</p>
                  <pre className="source-facts">{JSON.stringify(source.facts, null, 2)}</pre>
                  <p className="technical-id">Evidence: {source.evidence_id}</p>
                </details>
              </section>
            ))}
            <p className="technical-id">
              Source: {e.source_reference} {e.source_references.join(", ")}
            </p>
            <p className="technical-id">
              Execution: {e.tool_execution_id} · Evidence: {e.evidence_id}
            </p>
            <p>
              {e.validation_status} · {e.collected_at}
            </p>
          </article>
        ))}
      </section>
      {result.reconciliation && <section className="tool-detail" aria-label="Evidence reconciliation">
        <h2>Evidence reconciliation</h2>
        {result.reconciliation.conflicts.length === 0 && <p>No supported conflicts detected in this bounded evidence set.</p>}
        {result.reconciliation.conflicts.map(c => <article key={c.conflict_id} role="alert">
          <h3>{c.severity} · {c.conflict_type}</h3><p>{c.explanation}</p><p>{c.required_follow_up}</p>
          <EvidenceLinks ids={c.evidence_ids} />
        </article>)}
        <h3>Evidence gaps</h3>
        {result.reconciliation.gaps.map(g => <p key={g.gap_id}>{g.explanation}</p>)}
        <h3>Grounded source findings</h3>
        {result.reconciliation.grounded_findings.map((f, i) => <article key={i}><strong>{f.kind}</strong><p>{f.text}</p><EvidenceLinks ids={f.evidence_ids} /></article>)}
      </section>}
      <section className="tool-detail">
        <h2>Evidence-grounded interpretation</h2>
        <ul>
          {result.findings.map((f, i) => (
            <li key={i}>
              {f.text}
              <p className="technical-id">
                Evidence: {f.evidence_ids.join(", ")}
              </p>
            </li>
          ))}
        </ul>
      </section>
      <section className="tool-detail">
        <h2>Advisory recommendations</h2>
        <p>
          Human review recommended:{" "}
          {result.human_review_recommended ? "Yes" : "No"}
        </p>
        <ul>
          {result.recommended_next_steps.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
        <h3>Uncertainty and missing evidence</h3>
        <ul>
          {result.uncertainty.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      </section>
    </section>
  );
}

function EvidenceLinks({ ids }: { ids: string[] }) {
  return <p className="technical-id">Sources: {ids.map((id, i) => <span key={id}>{i > 0 ? ", " : ""}<a href={`#evidence-${id}`}>Inspect evidence {i + 1}</a></span>)}</p>;
}
