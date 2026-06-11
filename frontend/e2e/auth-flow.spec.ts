import { test, expect } from "@playwright/test";

/**
 * REAL Keycloak auth round-trip — deliberately does NOT use the mocked session in
 * e2e/utils/auth.ts. Exercises the exact browser flow the mock hides:
 *   login button → Keycloak form → dashboard → logout → SSO actually cleared.
 * Regression test for the federated-logout bug (missing id_token_hint / SSO
 * persistence → silent re-login straight to the dashboard).
 *
 *   PLAYWRIGHT_NO_WEBSERVER=1 PLAYWRIGHT_BASE_URL=http://aria.localhost \
 *   E2E_TEST_USER=... E2E_TEST_PASS=... npx playwright test auth-flow
 */
const USER = process.env.E2E_TEST_USER;
const PASS = process.env.E2E_TEST_PASS;

test.describe("real Keycloak auth flow", () => {
  test.skip(!USER || !PASS, "set E2E_TEST_USER / E2E_TEST_PASS (+ Keycloak up) to run");

  test("login → dashboard → logout → SSO cleared (login needs a fresh form)", async ({ page }) => {
    const loginButton = () => page.getByRole("button", { name: /login with keycloak/i });

    // 1) unauthenticated landing shows the login button
    await page.goto("/");
    await expect(loginButton()).toBeVisible();

    // 2) login button → Keycloak form → submit
    await loginButton().click();
    await page.waitForURL(/openid-connect\/auth/i);
    await page.fill("#username", USER!);
    await page.fill("#password", PASS!);
    await page.click("#kc-login, input[type=submit], button[type=submit]");

    // 3) back on the app, authenticated → dashboard (no login button)
    await page.waitForURL((u) => !/openid-connect/.test(u.toString()));
    await expect(loginButton()).toHaveCount(0);

    // 4) logout via /chat
    await page.goto("/chat");
    await page.getByRole("button", { name: /logout/i }).first().click();
    await page.waitForLoadState("networkidle");

    // 5) landing shows the login button again (NextAuth session cleared)
    await page.goto("/");
    await expect(loginButton()).toBeVisible();

    // 6) DEFINITIVE: clicking login must now require a real Keycloak form (SSO cleared).
    //    If SSO had persisted (the bug), this silently bounces to the dashboard and
    //    #username never appears → this assertion fails and catches the regression.
    await loginButton().click();
    await expect(page.locator("#username")).toBeVisible({ timeout: 15000 });
  });
});
