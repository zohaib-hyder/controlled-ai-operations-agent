import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
export function businessSnapshot(tenant: 0 | 1, includeJobState = false) {
  const root = resolve(process.cwd(), "..");
  return JSON.parse(execFileSync(resolve(root, "backend/.venv/bin/python"), ["scripts/browser_business_snapshot.py", "--tenant", String(tenant), ...(includeJobState ? ["--include-job-state"] : [])], { cwd: root, env: process.env, timeout: 10000, encoding: "utf8" })) as { counts: Record<string, number>; sha256: string };
}
