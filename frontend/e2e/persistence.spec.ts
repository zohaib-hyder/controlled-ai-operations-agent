import { test, expect } from "@playwright/test";
const password = process.env.DEMO_PASSWORD;
if (!password) throw new Error("Set local DEMO_PASSWORD");
async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page
    .getByLabel("Email", { exact: true })
    .fill("reviewer.0@example.com");
  await page.getByLabel("Password", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Workspace overview" }),
  ).toBeVisible();
}
test("persistent history, detail, events and evidence survive refresh", async ({
  page,
}) => {
  await login(page);
  const customer = (
    await (await page.request.get("/api/v1/customers?limit=100")).json()
  ).items.find((c: { name: string }) => c.name === "Fictional Client 0-00");
  const goal = `Phase 4 durable browser investigation ${test.info().project.name} ${Date.now()}`;
  const key = crypto.randomUUID();
  const response = await page.request.post("/api/v1/investigations", {
    headers: { Origin: "http://localhost:3000", "Idempotency-Key": key },
    data: { goal, customer_id: customer.id },
  });
  expect(response.status()).toBe(200);
  const result = await response.json();
  expect(result.status).toBe("COMPLETED");
  const duplicate = await page.request.post("/api/v1/investigations", {
    headers: { Origin: "http://localhost:3000", "Idempotency-Key": key },
    data: { goal, customer_id: customer.id },
  });
  expect((await duplicate.json()).investigation_id).toBe(
    result.investigation_id,
  );
  await page.goto("/investigations");
  await expect(
    page.getByRole("heading", { name: "Investigation history", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: goal, exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Investigation detail", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("COMPLETED", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Checkpoint and recovery", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Persistent execution events",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByText(/investigation_completed/)).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Verified retrieval evidence",
      exact: true,
    }),
  ).toBeVisible();
  await page.reload();
  await expect(page.getByText("COMPLETED", { exact: true })).toBeVisible();
  await expect(
    page.getByText(`Investigation ID: ${result.investigation_id}`),
  ).toBeVisible();
  await page.screenshot({
    path: test.info().outputPath("persistent-detail.png"),
    fullPage: true,
  });
  await page
    .getByRole("link", { name: "Back to Investigation Workspace", exact: true })
    .click();
  await page
    .getByLabel("Status filter", { exact: true })
    .selectOption("COMPLETED");
  await page
    .getByLabel("Customer reference", { exact: true })
    .fill(customer.id);
  await page
    .getByRole("button", { name: "Search history", exact: true })
    .click();
  await expect(
    page.getByRole("link", { name: goal, exact: true }),
  ).toBeVisible();
});
test("authorized cancellation persists on detail reload", async ({ page }) => {
  const id =
    process.env[`PHASE4_CANCEL_${test.info().project.name.toUpperCase()}`];
  if (!id)
    throw new Error("Seed Phase 4 lifecycle fixtures before browser tests");
  await login(page);
  await page.goto(`/investigations/${id}`);
  await expect(page.getByText("CREATED", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Request cancellation", exact: true })
    .click();
  await expect(page.getByText("CANCELLED", { exact: true })).toBeVisible();
  await expect(page.getByText(/cancellation_requested/).first()).toBeVisible();
  await page.reload();
  await expect(page.getByText("CANCELLED", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Attempt safe recovery", exact: true }),
  ).toHaveCount(0);
});
test("safe recovery exposes incomplete tool uncertainty without replay", async ({
  page,
}) => {
  const id =
    process.env[`PHASE4_RECOVERY_${test.info().project.name.toUpperCase()}`];
  if (!id)
    throw new Error("Seed Phase 4 lifecycle fixtures before browser tests");
  await login(page);
  await page.goto(`/investigations/${id}`);
  await expect(
    page.getByRole("button", { name: "Attempt safe recovery", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Attempt safe recovery", exact: true })
    .click();
  await expect(page.getByText("NEEDS_REVIEW", { exact: true })).toBeVisible();
  await expect(
    page.getByText("interrupted_tool_requires_review", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/recovery_attempted/)).toBeVisible();
  await expect(page.getByText(/recovery_completed/)).toBeVisible();
  await page.reload();
  await expect(page.getByText("NEEDS_REVIEW", { exact: true })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
