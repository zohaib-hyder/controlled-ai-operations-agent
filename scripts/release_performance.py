"""Bounded read-only LOCAL API latency baseline; never a production capacity claim."""

import argparse
import json
import math
import os
import platform
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
PATHS = {
    "health": "/health",
    "ready": "/ready",
    "customers": "/customers?limit=20",
    "investigation_history": "/investigations?limit=20",
    "approval_queue": "/approvals?limit=20",
    "execution_jobs": "/execution-jobs?limit=20",
    "operations": "/operations/overview",
    "incidents": "/incidents?limit=20",
}


def summarize(rows, duration):
    values = sorted(row[1] for row in rows)

    def percentile(p):
        return values[max(0, math.ceil(len(values) * p) - 1)] if values else None

    return dict(
        request_count=len(rows),
        success_count=sum(r[0] for r in rows),
        error_count=sum(not r[0] for r in rows),
        p50_ms=statistics.median(values) if values else None,
        p95_ms=percentile(0.95),
        p99_ms=percentile(0.99) if len(values) >= 100 else None,
        throughput_per_second=len(rows) / duration if duration else 0,
        duration_seconds=duration,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--max-p95-ms", type=float, default=None)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts/performance.json"
    )
    args = parser.parse_args()
    if args.max_p95_ms is not None and not 0 < args.max_p95_ms <= 10000:
        parser.error("max-p95-ms must be positive and at most 10000")
    if not 1 <= args.samples <= 200 or not 1 <= args.concurrency <= 20:
        parser.error("samples must be 1..200; concurrency 1..20")
    if os.environ.get("AI_PROVIDER", "mock") != "mock":
        parser.error("mock mode required")
    password = os.environ.get("DEMO_PASSWORD") or dotenv_values(ROOT / ".env").get(
        "DEMO_PASSWORD"
    )
    if not password:
        parser.error("Generate and seed ignored local credential first")
    with httpx.Client(
        base_url="http://127.0.0.1:8000/api/v1",
        timeout=15,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        start = time.perf_counter()
        auth = client.post(
            "/auth/login",
            headers={"Origin": "http://localhost:3000"},
            json={"email": "admin.0@example.com", "password": password},
        )
        authentication = summarize(
            [(auth.status_code == 200, (time.perf_counter() - start) * 1000)],
            time.perf_counter() - start,
        )
        auth.raise_for_status()
        results = {}
        for name, path in PATHS.items():

            def request(_, endpoint=path):
                start = time.perf_counter()
                try:
                    response = client.get(endpoint)
                    success = response.status_code == 200
                except httpx.HTTPError:
                    success = False
                return success, (time.perf_counter() - start) * 1000

            started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                rows = list(pool.map(request, range(args.samples)))
            results[name] = summarize(rows, time.perf_counter() - started)
        logout = client.post(
            "/auth/logout", headers={"Origin": "http://localhost:3000"}
        )
        results["authentication"] = authentication
    target_violations = [
        name
        for name, result in results.items()
        if name != "authentication"
        and args.max_p95_ms is not None
        and result["p95_ms"] > args.max_p95_ms
    ]
    report = dict(
        max_read_p95_ms=args.max_p95_ms,
        target_violations=target_violations,
        environment=dict(
            python=platform.python_version(),
            platform=platform.platform(),
            logical_cpus=os.cpu_count(),
        ),
        concurrency=args.concurrency,
        samples_per_read_endpoint=args.samples,
        measurements=results,
        logout_status=logout.status_code,
        limitations=[
            "Read-only HTTP baseline; no write workflow or worker capacity evidence",
            "Single authentication sample; no authentication percentiles inferred",
            "p99 omitted below 100 samples",
            "Latency includes response failures, if any; no warmup discarded",
        ],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return int(
        bool(target_violations)
        or any(r["error_count"] for r in results.values())
        or logout.status_code not in {200, 204}
    )


if __name__ == "__main__":
    sys.exit(main())
