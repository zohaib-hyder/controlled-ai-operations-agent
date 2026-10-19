import base from "./playwright.config";
import { defineConfig } from "@playwright/test";
const origin = process.env.RELEASE_BROWSER_ORIGIN ?? "http://127.0.0.1:3000";
if (!["http://127.0.0.1:3000", "http://127.0.0.1:13000"].includes(origin)) {
  throw new Error("Release browser requires a fixed local synthetic origin");
}
export default defineConfig(base, {
  use: { baseURL: origin },
  webServer: origin === "http://127.0.0.1:3000" ? base.webServer : undefined,
  testDir: "./release-e2e",
  timeout: 90000,
  retries: 0,
  workers: 1,
  reporter: [["list"], ["json", { outputFile: "../artifacts/release-browser-results.json" }]],
});
