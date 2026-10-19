import { businessSnapshot } from "./business-snapshot";
import { readFileSync } from "node:fs";
import { test, expect } from "@playwright/test";
const password=process.env.DEMO_PASSWORD;
test("execution jobs shows durable queue and rejects invalid bindings",async({page})=>{
  await page.goto("/login");
  await page.getByLabel("Email",{exact:true}).fill("operator.0@example.com");
  await page.getByLabel("Password",{exact:true}).fill(password!);
  await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Workspace overview"})).toBeVisible();
  await page.getByRole("link",{name:"Execution jobs"}).click();
  await expect(page.getByRole("heading",{name:"Execution jobs",exact:true})).toBeVisible();
  await expect(page.getByRole("heading",{name:"Queue visibility"})).toBeVisible();
  await page.getByLabel("Proposal ID",{exact:true}).fill("00000000-0000-0000-0000-000000000000");
  await page.getByLabel("Decision ID",{exact:true}).fill("00000000-0000-0000-0000-000000000000");
  await page.getByRole("button",{name:"Submit durable job"}).click();
  await expect(page.getByRole("alert").filter({hasText:"Proposal not found"})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});

test("durable submission, actual timeline and authorized cancellation",async({page})=>{
  await page.goto("/login");
  await page.getByLabel("Email",{exact:true}).fill("admin.1@example.com");
  await page.getByLabel("Password",{exact:true}).fill(password!);
  await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Workspace overview"})).toBeVisible();
  const beforeBusiness=businessSnapshot(1);
  const customers=await (await page.request.get("/api/v1/customers")).json();
  const customer=customers.items.find((c:{name:string})=>c.name==="Fictional Client 1-03");
  expect(customer).toBeTruthy();
  const headers={Origin:"http://localhost:3000"};
  const investigation=await page.request.post("/api/v1/investigations",{headers,data:{goal:"Synthetic durable browser cancellation proof",customer_id:customer.id}});
  expect(investigation.ok()).toBeTruthy();
  const view=await investigation.json();
  const references=view.evidence.flatMap((e:{sources:{source_type:string;evidence_id:string}[]})=>e.sources).filter((s:{source_type:string})=>s.source_type==="customer").map((s:{evidence_id:string})=>s.evidence_id);
  const response=await page.request.post("/api/v1/action-proposals",{headers,data:{investigation_id:view.investigation_id,action_name:"create_customer_note",target_resource_id:customer.id,arguments:{content:"Fictional browser queued note"},evidence_references:references,reason:"Synthetic queued cancellation verification"}});
  expect(response.ok()).toBeTruthy();
  const proposed=await response.json();expect(proposed.receipt.decision).toBe("ALLOW");
  await page.goto("/execution-jobs");
  await page.getByLabel("Proposal ID",{exact:true}).fill(proposed.proposal.proposal_id);
  await page.getByLabel("Decision ID",{exact:true}).fill(proposed.receipt.decision_id);
  await page.getByRole("button",{name:"Submit durable job"}).click();
  await expect(page.getByRole("heading",{name:"Job: QUEUED",exact:true})).toBeVisible();
  await expect(page.getByRole("heading",{name:"Job event timeline"})).toBeVisible();
  expect(businessSnapshot(1)).toEqual(beforeBusiness);
  await page.getByRole("button",{name:"Cancel job",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Job: CANCELLED",exact:true})).toBeVisible();
  await expect(page.getByRole("button",{name:"Retry with revalidation"})).toHaveCount(0);
  expect(businessSnapshot(1)).toEqual(beforeBusiness);
});

for (const state of ["DEAD_LETTERED", "RECONCILIATION_REQUIRED"] as const) {
  test(`${state} is visible and cannot be repaired by an unrelated administrator`, async ({page}) => {
    const path=process.env.PHASE10_BROWSER_FIXTURE_PATH;
    if (!path) throw new Error("Prepare explicit Phase 10 synthetic job fixtures");
    const fixture=JSON.parse(readFileSync(path,"utf8"))[0] as {job_id:string;uncertain_job_id:string};
    const id=state==="DEAD_LETTERED"?fixture.job_id:fixture.uncertain_job_id;
    const before=businessSnapshot(1,true);
    await page.goto("/login");
    await page.getByLabel("Email",{exact:true}).fill("admin.1@example.com");
    await page.getByLabel("Password",{exact:true}).fill(password!);
    await page.getByRole("button",{name:"Sign in",exact:true}).click();
    await expect(page.getByRole("heading",{name:"Workspace overview"})).toBeVisible();
    await page.goto("/execution-jobs");
    const ownCard=page.locator("article").filter({hasText:id});
    await expect(ownCard).toHaveCount(1);
    await ownCard.getByRole("button").click();
    await expect(page.getByRole("heading",{name:`Job: ${state}`,exact:true})).toBeVisible();
    await expect(page.getByText(state==="DEAD_LETTERED"?"Retry budget exhausted. Authorized retry must pass current security checks.":"Outcome needs evidence reconciliation. No blind retry.",{exact:true})).toBeVisible();
    await expect(page.getByRole("button",{name:"Retry with revalidation",exact:true})).toHaveCount(0);
    const response=await page.request.post(`/api/v1/execution-jobs/${id}/retry`,{headers:{Origin:"http://localhost:3000"},data:{}});
    expect(response.status()).toBe(403);
    expect((await (await page.request.get(`/api/v1/execution-jobs/${id}`)).json()).status).toBe(state);
    expect(businessSnapshot(1,true)).toEqual(before);
  });
}
