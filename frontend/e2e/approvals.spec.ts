import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
const password=process.env.DEMO_PASSWORD;
const fixturePath=process.env.PHASE8_BROWSER_FIXTURE_PATH;
test.skip(!fixturePath,"Explicit Phase 8 local fixture setup required");
async function login(page:import("@playwright/test").Page,role:string){
  await page.goto("/login");await page.getByLabel("Email",{exact:true}).fill(`${role}.1@example.com`);await page.getByLabel("Password",{exact:true}).fill(password!);await page.getByRole("button",{name:"Sign in",exact:true}).click();await expect(page.getByRole("heading",{name:"Workspace overview"})).toBeVisible();
}
test("independent review, controlled execution and before/after receipt",async({page,browser},testInfo)=>{
  const fixtures=JSON.parse(readFileSync(fixturePath!,"utf8")) as Record<string,string>;
  const id=fixtures[testInfo.project.name==="desktop"?"9":"7"];
  await login(page,"phase8.executor");await page.goto(`/action-proposals/approval/${id}`);
  await expect(page.getByText(/self-approval is prohibited/)).toBeVisible();await expect(page.getByRole("button",{name:"Approve action",exact:true})).toHaveCount(0);
  const reviewer=await browser.newContext();const reviewPage=await reviewer.newPage();await login(reviewPage,"reviewer");await reviewPage.goto("/approvals");await expect(reviewPage.getByRole("heading",{name:"Approval queue"})).toBeVisible();await reviewPage.goto(`/action-proposals/approval/${id}`);await expect(reviewPage.getByRole("heading",{name:"Supporting evidence"})).toBeVisible();await reviewPage.getByLabel("Review reason").fill("Independent synthetic browser evidence review");await reviewPage.getByRole("button",{name:"Approve action",exact:true}).click();await expect(reviewPage.getByRole("heading",{name:"APPROVED",exact:true})).toBeVisible();
  await page.reload();await page.getByRole("button",{name:"Execute approved action",exact:true}).click();await expect(page.getByRole("heading",{name:"Execution: COMMITTED"})).toBeVisible();await expect(page.getByText("Outcome verified: Yes",{exact:true})).toBeVisible();await expect(page.getByRole("heading",{name:"Before",exact:true})).toBeVisible();await expect(page.getByRole("heading",{name:"After",exact:true})).toBeVisible();await expect(page.getByText("execution_verified",{exact:false})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);await reviewer.close();
});
test("review rejection and inaccessible approval errors",async({page},testInfo)=>{
  const fixtures=JSON.parse(readFileSync(fixturePath!,"utf8")) as Record<string,string>;
  const id=fixtures[testInfo.project.name==="desktop"?"8":"6"];
  await login(page,"reviewer");await page.goto(`/action-proposals/approval/${id}`);await page.getByLabel("Review reason").fill("Synthetic evidence requires a different follow-up");await page.getByRole("button",{name:"Reject action",exact:true}).click();await expect(page.getByRole("heading",{name:"REJECTED",exact:true})).toBeVisible();await expect(page.getByRole("button",{name:"Execute approved action",exact:true})).toHaveCount(0);await page.goto("/action-proposals/approval/00000000-0000-0000-0000-000000000000");await expect(page.getByRole("alert").filter({hasText:"Approval unavailable"})).toBeVisible();
});
