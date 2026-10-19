import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  retries: 0,
  reporter: [["list"], ["json", { outputFile: "../artifacts/browser-results.json" }]],
  use: { baseURL: "http://127.0.0.1:3000" },
  webServer: {
    command: "npm run start -- --hostname 127.0.0.1",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: !process.env.CI,
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1440, height: 1000 } } },
    { name: "mobile", use: { viewport: { width: 390, height: 844 } } },
  ],
});
