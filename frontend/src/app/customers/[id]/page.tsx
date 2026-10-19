"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
export default function CustomerDetail() {
  const { id } = useParams<{ id: string }>();
  const [customer, setCustomer] = useState<{ id: string; name: string } | null>(
    null,
  );
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    api<{ id: string; name: string }>(`/customers/${encodeURIComponent(id)}`, {
      signal: controller.signal,
    })
      .then(setCustomer)
      .catch((error) => {
        if (!controller.signal.aborted)
          setError(
            error instanceof ApiError && error.status === 404
              ? "Customer not found or unavailable in your tenant."
              : "Unable to load customer.",
          );
      });
    return () => controller.abort();
  }, [id]);
  return (
    <>
      <Link className="data-link" href="/customers">
        ← Customers
      </Link>
      <p className="eyebrow">SYNTHETIC CUSTOMER · READ ONLY</p>
      {error ? (
        <section className="placeholder">
          <h1>Customer unavailable</h1>
          <p role="alert">{error}</p>
        </section>
      ) : !customer ? (
        <p role="status">Loading customer…</p>
      ) : (
        <section className="data-panel customer-detail">
          <h1>{customer.name}</h1>
          <p className="muted">Reference: {customer.id}</p>
          <p>
            Contact information is omitted from this view. No customer mutation
            actions are available.
          </p>
        </section>
      )}
    </>
  );
}
