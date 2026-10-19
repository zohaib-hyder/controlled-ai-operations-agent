import Link from "next/link";
export default function Page() {
  return (
    <>
      <p className="eyebrow">PHASE 1 · ACCESS CONTROL</p>
      <h1>Settings</h1>
      <section className="placeholder">
        <span className="scenario-id" aria-hidden="true">
          ◇
        </span>
        <h2>Not yet implemented</h2>
        <p>
          This area is reserved for a later phase. No live customer data, agent
          execution, approvals or operational writes are available.
        </p>
        <Link className="button" href="/">
          Back to overview
        </Link>
      </section>
    </>
  );
}
