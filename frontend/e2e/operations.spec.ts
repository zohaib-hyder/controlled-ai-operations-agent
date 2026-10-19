import { businessSnapshot } from "./business-snapshot";
import {test,expect} from "@playwright/test";
import {readFileSync} from "node:fs";
const password=process.env.DEMO_PASSWORD;
const fixturePath=process.env.PHASE10_BROWSER_FIXTURE_PATH;
const fixtures=()=>JSON.parse(readFileSync(fixturePath!,"utf8")) as {incident_id:string;job_id:string;proposal_id:string;investigation_id:string}[];
async function login(page:import("@playwright/test").Page,email:string){await page.goto("/login");await page.getByLabel("Email",{exact:true}).fill(email);await page.getByLabel("Password",{exact:true}).fill(password!);await page.getByRole("button",{name:"Sign in",exact:true}).click();await expect(page.getByRole("heading",{name:"Workspace overview"})).toBeVisible();}

test("Command Center loads real KPIs, filters UTC time and reports an empty cohort",async({page})=>{
 await login(page,"admin.1@example.com");await page.goto("/operations");await expect(page.getByRole("heading",{name:"Operations Command Center",exact:true})).toBeVisible();await expect(page.getByRole("heading",{name:"Pipeline diagnostics"})).toBeVisible();await expect(page.getByRole("heading",{name:"Investigation volume by UTC day"})).toBeVisible();
 await page.getByLabel("Time range",{exact:true}).selectOption("7d");await expect(page.getByText(/Cohort \[/)).toBeVisible();
 await page.getByLabel("Time range",{exact:true}).selectOption("custom");await page.getByLabel("Start UTC",{exact:true}).fill("2099-01-01T00:00");await page.getByLabel("End UTC",{exact:true}).fill("2099-01-02T00:00");await page.getByRole("button",{name:"Apply custom range"}).click();await expect(page.getByText("No samples in this range.").first()).toBeVisible();await expect(page.getByText(/Terminal job success: No samples/)).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test("Command Center error state does not retain healthy pipeline cards",async({page})=>{
 await login(page,"operator.0@example.com");await page.route("**/api/v1/operations/overview*",route=>route.fulfill({status:503,contentType:"application/json",body:JSON.stringify({error:{message:"Synthetic diagnostics unavailable"}})}));await page.goto("/operations");await expect(page.getByRole("alert").filter({hasText:"Operational signals unavailable"})).toBeVisible();await expect(page.getByRole("heading",{name:"Pipeline diagnostics"})).toHaveCount(0);
});

test("reviewer acknowledges and resolves an incident without job repair",async({page},testInfo)=>{
 test.skip(!fixturePath,"Explicit synthetic Phase 10 fixtures required");const before=businessSnapshot(1,true);const fixture=fixtures()[testInfo.project.name==="desktop"?1:2];
 await login(page,"reviewer.1@example.com");await page.goto("/incidents");await page.getByLabel("Incident severity",{exact:true}).selectOption("critical");await page.goto(`/incidents/${fixture.incident_id}`);await expect(page.getByRole("heading",{name:"Incident response"})).toBeVisible();await page.getByLabel("Operator note",{exact:true}).fill("Synthetic incident acknowledged; underlying action remains restricted");await page.getByRole("button",{name:"acknowledge incident",exact:true}).click();await expect(page.getByText("ACKNOWLEDGED",{exact:true})).toBeVisible();await page.getByLabel("Operator note",{exact:true}).fill("Synthetic incident review resolved; no business repair performed");await page.getByRole("button",{name:"resolve incident",exact:true}).click();await expect(page.getByText("RESOLVED",{exact:true})).toBeVisible();await expect(page.getByText("incident_resolved",{exact:true})).toBeVisible();
 const job=await page.request.get(`/api/v1/operations/correlations/${fixture.job_id}`);expect(job.status()).toBe(200);expect((await job.json()).links.some((l:{id:string})=>l.id===fixture.job_id)).toBe(true);expect(businessSnapshot(1,true)).toEqual(before);
});

test("auditor reads incident history and cannot mutate; foreign tenant cannot inspect",async({page})=>{
 test.skip(!fixturePath,"Explicit synthetic Phase 10 fixtures required");const fixture=fixtures()[0];await login(page,"auditor.1@example.com");await page.goto(`/incidents/${fixture.incident_id}`);await expect(page.getByText(/Read-only operational history/)).toBeVisible();await expect(page.getByRole("button",{name:/incident$/})).toHaveCount(0);expect((await page.request.post(`/api/v1/incidents/${fixture.incident_id}/acknowledge`,{headers:{Origin:"http://localhost:3000"},data:{note:"Auditor mutation must fail"}})).status()).toBe(403);
 const loggedOut=page.waitForResponse(r=>r.url().endsWith("/api/v1/auth/logout")&&r.request().method()==="POST");
 await page.getByRole("button",{name:"Sign out"}).click();
 expect((await loggedOut).ok()).toBe(true);
 await expect(page.getByRole("heading",{name:"Sign in to Northstar",exact:true})).toBeVisible();
 expect((await page.request.get("/api/v1/auth/me")).status()).toBe(401);
 await login(page,"admin.0@example.com");
 expect((await page.request.get(`/api/v1/incidents/${fixture.incident_id}`)).status()).toBe(404);
 expect((await page.request.get(`/api/v1/operations/correlations/${fixture.job_id}`)).status()).toBe(404);
});

test("diagnostics follows persisted correlation links",async({page})=>{
 test.skip(!fixturePath,"Explicit synthetic Phase 10 fixtures required");const fixture=fixtures()[0];await login(page,"admin.1@example.com");await page.goto(`/diagnostics?trace=${fixture.job_id}`);await expect(page.getByLabel("Correlation or entity ID",{exact:true})).toHaveValue(fixture.job_id);await page.getByRole("button",{name:"Trace operations",exact:true}).click();await expect(page.getByRole("heading",{name:"Related records"})).toBeVisible();await expect(page.getByRole("heading",{name:"End-to-end operational timeline"})).toBeVisible();await page.locator("section").filter({has:page.getByRole("heading",{name:"Related records",exact:true})}).getByRole("link",{name:`investigation: ${fixture.investigation_id}`,exact:true}).click();await expect(page.getByLabel("Correlation or entity ID",{exact:true})).toHaveValue(fixture.investigation_id);await page.getByRole("button",{name:"Trace operations",exact:true}).click();await expect(page.locator("section").filter({has:page.getByRole("heading",{name:"Related records",exact:true})}).getByRole("link",{name:`job: ${fixture.job_id}`,exact:true})).toBeVisible();
});
