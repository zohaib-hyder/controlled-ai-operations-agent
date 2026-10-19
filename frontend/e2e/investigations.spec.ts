import { test, expect } from "@playwright/test";
const password = process.env.DEMO_PASSWORD;
if (!password) throw new Error("Set local DEMO_PASSWORD");
async function login(page: import("@playwright/test").Page, role = "operator") {
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(`${role}.0@example.com`);
  await page.getByLabel("Password", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Workspace overview" }),
  ).toBeVisible();
}
test("investigation form renders real evidence and advisory findings", async ({
  page,
}) => {
  await login(page);
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Investigations", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Investigation Workspace" }),
  ).toBeVisible();
  await page
    .getByLabel("Customer", { exact: true })
    .selectOption({ label: "Fictional Client 0-00" });
  await page
    .getByLabel("Investigation goal", { exact: true })
    .fill("Investigate the unpaid invoice account block");
  await page
    .getByRole("button", { name: "Run read-only investigation" })
    .click();
  const result = page.getByRole("region", { name: "Investigation result" });
  await expect(result).toBeVisible({ timeout: 15000 });
  await expect(result.getByText("COMPLETED", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Verified retrieval evidence" }),
  ).toBeVisible();
  await expect(
    result.getByText(/Account status: blocked/).first(),
  ).toBeVisible();
  await expect(result.getByText(/authorized billing operator/)).toBeVisible();
  await expect(result.getByText(/schema_validated/).first()).toBeVisible();
  const trace = result.getByRole("region", { name: "Planner execution trace" });
  await expect(trace.getByText("Deterministic mock", { exact: true })).toBeVisible();
  await expect(trace.getByText(/Planning iterations:/)).toBeVisible();
  await expect(trace.getByRole("link", { name: "Inspect decision observation", exact: true }).first()).toBeVisible();
  await expect(result.getByRole("heading", { name: "Evidence reconciliation", exact: true })).toBeVisible();
  const sourceLink = result.getByRole("link", { name: "Inspect evidence 1", exact: true }).first();
  await sourceLink.click();
  await expect(page).toHaveURL(/#evidence-/);
  const source = result.locator("section:target");
  await source.getByText("Inspect source details", { exact: true }).click();
  await expect(source.getByText(/Source timestamp:/)).toBeVisible();
  await expect(result.getByText(/policy · STALE/).first()).toBeVisible();
  await page.screenshot({
    path: test.info().outputPath("investigation.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
test("security review and resource errors are explicit", async ({ page }) => {
  await login(page);
  await page.goto("/investigations");
  await page
    .getByLabel("Customer", { exact: true })
    .selectOption({ label: "Fictional Client 0-01" });
  await page
    .getByLabel("Investigation goal", { exact: true })
    .fill("Review the security hold without modifying anything");
  await page
    .getByRole("button", { name: "Run read-only investigation" })
    .click();
  await expect(
    page
      .getByRole("region", { name: "Investigation result" })
      .getByText("NEEDS_REVIEW", { exact: true }),
  ).toBeVisible({
    timeout: 15000,
  });
  await expect(
    page.getByText(/Escalate to an authorized security reviewer/),
  ).toBeVisible();
  await page.route("**/api/v1/investigations", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: { message: "Investigation service unavailable" },
      }),
    }),
  );
  await page
    .getByRole("button", { name: "Run read-only investigation" })
    .click();
  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: "Investigation service unavailable" }),
  ).toContainText("Investigation service unavailable");
});
test("auditor cannot open investigation workspace", async ({ page }) => {
  await login(page, "auditor");
  await page.goto("/investigations");
  await expect(
    page.getByRole("heading", { name: "Access denied", exact: true }),
  ).toBeVisible();
  expect(
    (
      await page.request.post("/api/v1/investigations", {
        headers: { Origin: "http://localhost:3000" },
        data: {
          goal: "Inspect safely",
          customer_id: "00000000-0000-0000-0000-000000000000",
        },
      })
    ).status(),
  ).toBe(403);
});

test("payment conflict exposes grounded source links", async ({ page }) => {
  await login(page, "admin");
  await page.goto("/investigations");
  await page.getByLabel("Customer", { exact: true }).selectOption({ label: "Fictional Client 0-04" });
  await page.getByLabel("Investigation goal", { exact: true }).fill("Reconcile conflicting synthetic payment evidence");
  await page.getByRole("button", { name: "Run read-only investigation" }).click();
  const result = page.getByRole("region", { name: "Investigation result" });
  await expect(result.getByText("NEEDS_REVIEW", { exact: true })).toBeVisible({ timeout: 15000 });
  await expect(result.getByRole("alert").filter({ hasText: "payment_unresolved" })).toContainText("Payment allocation");
  await expect(result.getByRole("heading", { name: "Grounded source findings" })).toBeVisible();
});
