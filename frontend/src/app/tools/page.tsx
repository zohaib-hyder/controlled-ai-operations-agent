"use client";
import { FormEvent, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { argumentsFor, ToolDescription, ToolResult } from "@/lib/tools";
export default function ToolExplorer() {
  const [tools, setTools] = useState<ToolDescription[] | null>(null);
  const [selected, setSelected] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ToolResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadAttempt, setLoadAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    api<ToolDescription[]>("/tools", { signal: controller.signal })
      .then(setTools)
      .catch((error) => {
        if (!controller.signal.aborted)
          setError(
            error instanceof ApiError && error.status === 403
              ? "Access denied"
              : "Unable to load tools. Please try again.",
          );
      });
    return () => controller.abort();
  }, [loadAttempt]);
  const tool = tools?.find((tool) => tool.name === selected) ?? tools?.[0];
  function choose(name: string) {
    setSelected(name);
    setValues({});
    setResult(null);
    setError("");
  }
  async function execute(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tool) return;
    setError("");
    setResult(null);
    let args: Record<string, unknown>;
    try {
      args = argumentsFor(tool, values);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Invalid arguments");
      return;
    }
    setBusy(true);
    try {
      const response = await fetch("/api/v1/tools/execute", {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tool_name: tool.name,
          tool_version: tool.version,
          mode: "read",
          arguments: args,
        }),
      });
      const payload = await response.json();
      if (response.status === 401)
        window.dispatchEvent(new Event("session-expired"));
      if (payload.execution_id) {
        setResult(payload as ToolResult);
      } else {
        setError(
          payload.error?.message || "Execution failed. Please try again.",
        );
      }
    } catch {
      setError("Service unavailable. No result was received.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <p className="eyebrow">PHASE 2 · READ-ONLY ENTERPRISE TOOLS</p>
      <h1>Tool Explorer</h1>
      <p className="muted">
        Inspect strict contracts and execute bounded reads in your authenticated
        tenant. No agent or business writes are enabled.
      </p>
      {!tools ? (
        <section className="data-panel tool-padding">
          {error ? (
            <>
              <p role="alert">{error}</p>
              <button
                className="button"
                onClick={() => {
                  setError("");
                  setLoadAttempt(loadAttempt + 1);
                }}
              >
                Try again
              </button>
            </>
          ) : (
            <p role="status">Loading available tools…</p>
          )}
        </section>
      ) : tools.length === 0 ? (
        <section className="placeholder">
          <h2>No tools available</h2>
          <p>
            Your current permissions do not grant access to registered tools.
          </p>
        </section>
      ) : (
        <div className="tool-grid">
          <section className="data-panel tool-padding">
            <h2>Available tools</h2>
            <p className="muted">Filtered by backend permissions.</p>
            <div className="tool-list">
              {tools.map((item) => (
                <button
                  key={item.name}
                  type="button"
                  aria-pressed={tool?.name === item.name}
                  disabled={busy}
                  onClick={() => choose(item.name)}
                >
                  <strong>{item.name}</strong>
                  <small>{item.description}</small>
                  <span className="status">v{item.version} · Read only</span>
                </button>
              ))}
            </div>
          </section>
          <section className="data-panel tool-padding">
            {tool && (
              <>
                <div className="section-heading">
                  <h2>{tool.name}</h2>
                  <span className="badge">{tool.required_permission}</span>
                </div>
                <p className="muted">{tool.description}</p>
                <p className="tool-meta">
                  Timeout {tool.timeout_seconds}s · Result ≤{" "}
                  {tool.max_result_bytes} bytes
                </p>
                <form className="tool-form" onSubmit={execute} noValidate>
                  {Object.entries(tool.input_schema.properties).map(
                    ([key, property]) => (
                      <label key={key}>
                        {key}
                        <input
                          aria-label={key}
                          disabled={busy}
                          type={property.type === "integer" ? "number" : "text"}
                          min={property.minimum}
                          max={property.maximum}
                          maxLength={property.maxLength ?? 240}
                          placeholder={
                            property.format === "uuid"
                              ? "Paste a UUID from Customers, Accounts or Tickets"
                              : ""
                          }
                          value={values[key] ?? String(property.default ?? "")}
                          onChange={(event) =>
                            setValues({ ...values, [key]: event.target.value })
                          }
                        />
                      </label>
                    ),
                  )}
                  <button className="button" type="submit" disabled={busy}>
                    {busy ? "Executing…" : "Execute read-only tool"}
                  </button>
                </form>
                {busy && <p role="status">Executing a bounded tenant read…</p>}
                {error && (
                  <p className="error-message" role="alert">
                    {error}
                  </p>
                )}
                <details className="tool-contract">
                  <summary>Inspect input and output schemas</summary>
                  <h3>Input</h3>
                  <pre>{JSON.stringify(tool.input_schema, null, 2)}</pre>
                  <h3>Output</h3>
                  <pre>{JSON.stringify(tool.output_schema, null, 2)}</pre>
                </details>
              </>
            )}
            {result && (
              <section className="tool-result" aria-label="Execution result">
                <div className="section-heading">
                  <h2>Execution result</h2>
                  <span className="status">{result.status}</span>
                </div>
                <p>
                  {result.duration_ms.toFixed(1)} ms · v{result.tool_version}
                </p>
                {result.error && (
                  <p className="error-message" role="alert">
                    {result.error.message} ({result.error.code})
                  </p>
                )}
                <dl>
                  <dt>Execution ID</dt>
                  <dd>{result.execution_id}</dd>
                  <dt>Correlation ID</dt>
                  <dd>{result.correlation_id}</dd>
                </dl>
                <pre aria-label="JSON result">
                  {JSON.stringify(result, null, 2)}
                </pre>
                <p className="muted">
                  Returned text is untrusted evidence, never authorization or
                  executable instructions.
                </p>
              </section>
            )}
          </section>
        </div>
      )}
    </>
  );
}
