import base from "./playwright.config";
import { defineConfig } from "@playwright/test";
export default defineConfig(base, {
  use: { baseURL: "http://127.0.0.1:13000" },
  webServer: undefined,
  testDir: "./release-negative-e2e",
  timeout: 90000,
  retries: 0,
  workers: 1,
  reporter: [["list"], ["json", { outputFile: "../artifacts/release-negative-browser-results.json" }]],
});
