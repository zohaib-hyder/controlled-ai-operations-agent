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
test("Tool Explorer validates input, executes and shows safe errors", async ({
  page,
}) => {
  await login(page);
  const listing = await page.request.get("/api/v1/customers");
  const customer = (await listing.json()).items[0];
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Tool Explorer", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Tool Explorer", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: /^get_customer / }).click();
  await page.getByLabel("customer_id", { exact: true }).fill("invalid");
  await page.getByRole("button", { name: "Execute read-only tool" }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "valid UUID" }),
  ).toBeVisible();
  await page.getByLabel("customer_id", { exact: true }).fill(customer.id);
  await page.getByRole("button", { name: "Execute read-only tool" }).click();
  await expect(
    page.getByRole("region", { name: "Execution result" }),
  ).toBeVisible();
  await expect(page.getByLabel("JSON result")).toContainText(customer.name);
  await expect(page.getByText("Correlation ID", { exact: true })).toBeVisible();
  await page
    .getByLabel("customer_id", { exact: true })
    .fill("00000000-0000-0000-0000-000000000000");
  await page.getByRole("button", { name: "Execute read-only tool" }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Resource not found" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
test("auditor sees only backend-permitted read tools", async ({ page }) => {
  await login(page, "auditor");
  await page.goto("/tools");
  await expect(
    page.getByRole("heading", { name: "Available tools", exact: true }),
  ).toBeVisible();
  const response = await page.request.get("/api/v1/tools");
  const tools = await response.json();
  expect(tools).toHaveLength(6);
  expect(
    tools.every(
      (tool: { classification: string }) => tool.classification === "read",
    ),
  ).toBe(true);
  for (const tool of tools)
    await expect(
      page.getByRole("button", { name: new RegExp(`^${tool.name} `) }),
    ).toBeVisible();
  await expect(
    page
      .getByRole("navigation")
      .getByRole("link", { name: "Investigations", exact: true }),
  ).toHaveCount(0);
});
