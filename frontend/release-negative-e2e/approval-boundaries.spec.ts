import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
const password = process.env.DEMO_PASSWORD;
if (!password) throw new Error("Explicit local credential required");
for (const scenario of ["expired", "revoked", "stale"] as const) {
  test(`${scenario} authority cannot execute an approved action`, async ({page}, info) => {
    const root = resolve(process.cwd(), "..");
    const output = resolve(root, "artifacts", `negative-${scenario}-${info.project.name}.json`);
    execFileSync(resolve(root, "backend/.venv/bin/python"), ["scripts/prepare_release_negative.py", "--case", scenario, "--output", output, "--confirm-synthetic-demo"], {
      cwd: root,
      env: {...process.env, APP_ENV: "development", AI_PROVIDER: "mock", DATABASE_URL: process.env.RELEASE_DEMO_DATABASE_URL ?? "postgresql+psycopg://northstar:synthetic-local-only@localhost:55433/northstar_demo"},
      timeout: 40000,
    });
    const fixture = JSON.parse(readFileSync(output, "utf8"));
    await page.goto("/login");
    await page.getByLabel("Email", {exact:true}).fill(fixture.email);
    await page.getByLabel("Password", {exact:true}).fill(password!);
    await page.getByRole("button", {name:"Sign in",exact:true}).click();
    await expect(page.getByRole("heading", {name:"Workspace overview"})).toBeVisible();
    const before = await (await page.request.get(`/api/v1/accounts/${fixture.account_id}`)).json();
    await page.goto(`/action-proposals/approval/${fixture.approval_id}`);
    await expect(page.getByRole("heading", {name:scenario === "revoked" ? "Access denied" : scenario === "expired" ? "EXPIRED" : "INVALIDATED",exact:true})).toBeVisible();
    await expect(page.getByRole("button", {name:"Execute approved action",exact:true})).toHaveCount(0);
    if (scenario === "revoked") {
      await page.goto("/execution-jobs");
      await expect(page.getByRole("heading", {name:"Access denied",exact:true})).toBeVisible();
      await expect(page.getByRole("button", {name:"Submit durable job",exact:true})).toHaveCount(0);
    }
    const denied = await page.request.post(`/api/v1/action-proposals/${fixture.proposal_id}/execute`, {
      headers: {Origin:"http://localhost:3000", "Idempotency-Key":`negative-${crypto.randomUUID()}`},
      data: {decision_id:fixture.decision_id, approval_id:fixture.approval_id},
    });
    expect(denied.status()).toBe(scenario === "revoked" ? 403 : 409);
    expect(await (await page.request.get(`/api/v1/accounts/${fixture.account_id}`)).json()).toEqual(before);
    expect(before.status).toBe("blocked");
    expect(before.evidence_version).toBe(1);
  });
}

test("server-expired session clears the workspace and cannot execute", async ({page,browser},info) => {
  const root=resolve(process.cwd(),"..");
  const output=resolve(root,"artifacts",`negative-session-${info.project.name}.json`);
  const environment={...process.env,APP_ENV:"development",AI_PROVIDER:"mock",DATABASE_URL:process.env.RELEASE_DEMO_DATABASE_URL ?? "postgresql+psycopg://northstar:synthetic-local-only@localhost:55433/northstar_demo"};
  const command=["scripts/prepare_release_negative.py","--case","expired","--output",output,"--confirm-synthetic-demo"];
  execFileSync(resolve(root,"backend/.venv/bin/python"),command,{cwd:root,env:environment,timeout:40000});
  const fixture=JSON.parse(readFileSync(output,"utf8"));
  async function signIn(target:import("@playwright/test").Page,email:string) {
    await target.goto("/login");await target.getByLabel("Email",{exact:true}).fill(email);await target.getByLabel("Password",{exact:true}).fill(password!);await target.getByRole("button",{name:"Sign in",exact:true}).click();await expect(target.getByRole("heading",{name:"Workspace overview"})).toBeVisible();
  }
  await signIn(page,fixture.email);
  const before=await (await page.request.get(`/api/v1/accounts/${fixture.account_id}`)).json();
  execFileSync(resolve(root,"backend/.venv/bin/python"),[...command,"--expire-fixture-session"],{cwd:root,env:environment,timeout:20000});
  await page.goto("/customers");
  await expect(page.getByRole("heading",{name:"Sign in to Northstar",exact:true})).toBeVisible();
  expect((await page.request.get("/api/v1/auth/me")).status()).toBe(401);
  expect((await page.request.post(`/api/v1/action-proposals/${fixture.proposal_id}/execute`,{headers:{Origin:"http://localhost:3000","Idempotency-Key":`expired-${crypto.randomUUID()}`},data:{decision_id:fixture.decision_id,approval_id:fixture.approval_id}})).status()).toBe(401);
  const independent=await browser.newContext({viewport:page.viewportSize()!});
  try {
    const reviewer=await independent.newPage();await signIn(reviewer,"reviewer.1@example.com");
    expect(await (await reviewer.request.get(`/api/v1/accounts/${fixture.account_id}`)).json()).toEqual(before);
  } finally {await independent.close();}
});
