import { defineConfig } from "@playwright/test";

// Set PLAYWRIGHT_NO_WEBSERVER=1 to run against an already-running stack (e.g. the
// dockerized app at http://aria.localhost) instead of spawning a local `next dev`.
const noWebServer = !!process.env.PLAYWRIGHT_NO_WEBSERVER;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: 0,
  timeout: 60000,
  expect: { timeout: 15000 },
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3003",
    headless: true,
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    trace: "on-first-retry",
  },
  ...(noWebServer
    ? {}
    : {
        webServer: {
          command: "npm run dev",
          url: "http://localhost:3003",
          reuseExistingServer: !process.env.CI,
          timeout: 30000,
        },
      }),
});
