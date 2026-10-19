"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
type Kind = "customers" | "accounts" | "tickets";
interface Row {
  id: string;
  name?: string;
  subject?: string;
  status?: string;
  block_reason?: string | null;
  customer_id?: string;
  account_id?: string;
}
interface Page {
  items: Row[];
  total: number;
  limit: number;
  offset: number;
}
export function ResourceList({ kind }: { kind: Kind }) {
  const [data, setData] = useState<Page | null>(null);
  const [error, setError] = useState("");
  const [denied, setDenied] = useState(false);
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    api<Page>(`/${kind}?limit=20&offset=${offset}`, {
      signal: controller.signal,
    })
      .then(setData)
      .catch((error) => {
        if (controller.signal.aborted) return;
        setDenied(error instanceof ApiError && error.status === 403);
        setError(
          error instanceof Error ? error.message : "Unable to load records",
        );
      });
    return () => controller.abort();
  }, [kind, offset, attempt]);
  function reload() {
    setError("");
    setDenied(false);
    setData(null);
    setAttempt(attempt + 1);
  }
  function move(value: number) {
    setData(null);
    setError("");
    setOffset(value);
  }
  return (
    <>
      <p className="eyebrow">TENANT-SCOPED · READ ONLY</p>
      <h1 className="capitalize">{kind}</h1>
      <p className="muted">
        Synthetic records from your authenticated tenant. Operational writes are
        not implemented.
      </p>
      {error ? (
        <section className="placeholder">
          <h2>{denied ? "Access denied" : "Unable to load records"}</h2>
          <p role="alert">{error}</p>
          <button className="button" onClick={reload}>
            Try again
          </button>
        </section>
      ) : !data ? (
        <p className="auth-status" role="status">
          Loading {kind}…
        </p>
      ) : (
        <section className="data-panel">
          <div className="data-summary">
            {data.total} records in your tenant
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Reference</th>
                  <th>{kind === "customers" ? "Customer" : "Description"}</th>
                  {kind !== "customers" && <th>Status</th>}
                </tr>
              </thead>
              <tbody>
                {data.items.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <code>{row.id.slice(0, 8)}</code>
                    </td>
                    <td>
                      {kind === "customers" ? (
                        <Link
                          className="data-link"
                          href={`/customers/${row.id}`}
                        >
                          {row.name}
                        </Link>
                      ) : kind === "tickets" ? (
                        row.subject
                      ) : (
                        <>
                          <span>
                            {row.block_reason?.replaceAll("_", " ") ||
                              "No account restriction"}
                          </span>
                          <small className="muted">
                            Customer {row.customer_id?.slice(0, 8)}
                          </small>
                        </>
                      )}
                    </td>
                    {kind !== "customers" && (
                      <td>
                        <span className="status">{row.status}</span>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
            {data.items.length === 0 && (
              <p className="auth-status">No records found.</p>
            )}
          </div>
          <div className="pagination">
            <button
              disabled={offset === 0}
              onClick={() => move(Math.max(0, offset - 20))}
            >
              Previous
            </button>
            <span>
              {data.total === 0 ? 0 : offset + 1}–
              {Math.min(offset + 20, data.total)} of {data.total}
            </span>
            <button
              disabled={offset + 20 >= data.total || offset + 20 > 10000}
              onClick={() => move(offset + 20)}
            >
              Next
            </button>
          </div>
        </section>
      )}
    </>
  );
}
