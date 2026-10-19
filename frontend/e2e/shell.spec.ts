import { test, expect } from "@playwright/test";
import { randomBytes } from "node:crypto";
const password = process.env.DEMO_PASSWORD;
if (!password)
  throw new Error(
    "Set DEMO_PASSWORD to the local seeded fixture password before Playwright",
  );
async function login(page: import("@playwright/test").Page, role = "operator") {
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(`${role}.0@example.com`);
  await page.getByLabel("Password", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Workspace overview" }),
  ).toBeVisible();
}
test("login, tenant data, responsive navigation and logout", async ({
  page,
}) => {
  await login(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await expect(
    page
      .getByRole("navigation")
      .getByRole("link", { name: "Approvals", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Customers", exact: true })
    .click();
  await expect(page.getByText("10 records in your tenant")).toBeVisible();
  await page
    .getByRole("link", { name: /Fictional Client 0-/ })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: /Fictional Client 0-/ }),
  ).toBeVisible();
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Accounts", exact: true })
    .click();
  await expect(page.getByText("10 records in your tenant")).toBeVisible();
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Tickets", exact: true })
    .click();
  await expect(page.getByText("15 records in your tenant")).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(
    page.getByRole("heading", { name: "Sign in to Northstar" }),
  ).toBeVisible();
  expect((await page.request.get("/api/v1/auth/me")).status()).toBe(401);
});
test("unauthorized direct page access", async ({ page }) => {
  await login(page, "auditor");
  await page.goto("/settings");
  await expect(
    page.getByRole("heading", { name: "Access denied" }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("navigation")
      .getByRole("link", { name: "Investigations", exact: true }),
  ).toHaveCount(0);
});
test("expired or revoked session clears workspace", async ({
  page,
  context,
}) => {
  await login(page);
  const cookies = await context.cookies();
  const token = cookies.find((cookie) => cookie.name === "northstar_session")!;
  // Revoke the real server-side session outside React, then exercise stale UI state.
  const logout = await page.request.post("/api/v1/auth/logout", {
    headers: { Origin: "http://127.0.0.1:3000" },
  });
  expect(logout.status()).toBe(204);
  await context.addCookies([{ ...token }]);
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Customers", exact: true })
    .click();
  await expect(
    page.getByText("Your session has expired or was revoked. Sign in again."),
  ).toBeVisible();
});
test("invalid credentials remain generic", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill("missing@example.com");
  await page
    .getByLabel("Password", { exact: true })
    .fill(randomBytes(20).toString("hex"));
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator("form").getByRole("alert")).toHaveText(
    "Invalid email or password",
  );
});

test("browser cookie expiry clears stale authenticated presentation", async ({
  page,
  context,
}) => {
  await login(page);
  const cookie = (await context.cookies()).find(
    (cookie) => cookie.name === "northstar_session",
  )!;
  expect(cookie.httpOnly).toBe(true);
  await context.addCookies([
    { ...cookie, expires: Math.floor(Date.now() / 1000) - 60 },
  ]);
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Customers", exact: true })
    .click();
  await expect(
    page.getByText("Your session has expired or was revoked. Sign in again."),
  ).toBeVisible();
});

test("action proposals clearly remain evaluation only", async ({ page }) => {
  await login(page);
  await page.getByRole("navigation").getByRole("link", { name: "Action proposals", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Action proposals", exact: true })).toBeVisible();
  await expect(page.getByText(/ALLOW means policy eligibility/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Evaluate eligibility", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Execute", exact: true })).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
