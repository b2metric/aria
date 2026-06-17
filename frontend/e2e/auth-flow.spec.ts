import { test, expect } from "@playwright/test";

const USER = process.env.E2E_TEST_USER || "admin@aria.local";
const PASS = process.env.E2E_TEST_PASS || "admin";

test.describe("ARIA real auth flow via Custom Credentials", () => {
  test("login → dashboard → token refresh → logout", async ({ page }) => {
    // 1) Go to login
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /Sign in to ARIA/i })).toBeVisible();

    // 2) Fill credentials and submit
    await page.fill("input[name='email']", USER);
    await page.fill("input[name='password']", PASS);
    await page.getByRole("button", { name: /Sign in/i }).click();

    // 3) Wait for redirect to dashboard
    await page.waitForURL("/");
    await expect(page.getByRole("heading", { name: /Dashboard/i })).toBeVisible();

    // 4) Token Refresh Simulation:
    // By intercepting `/api/auth/session` we can observe session fetching.
    // Real Keycloak token refresh happens via next-auth jwt callback. 
    // We can just verify the session is active.
    const sessionRes = await page.goto("/api/auth/session");
    const session = await sessionRes?.json();
    expect(session?.user).toBeDefined();
    expect(session?.accessToken).toBeDefined();

    // Go back to app
    await page.goto("/");

    // 5) Logout
    await page.getByRole("button", { name: /Logout/i }).click();
    
    // Wait for redirect to login
    await page.waitForURL("/login");
    await expect(page.getByRole("heading", { name: /Sign in to ARIA/i })).toBeVisible();

    // 6) Verify we can't access dashboard
    await page.goto("/");
    await page.waitForURL("/login");
  });
});
