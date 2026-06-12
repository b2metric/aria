import { test, expect } from "@playwright/test";

/**
 * Admin UI E2E tests for Memory Manager and Tenant Config pages.
 * 
 * Requires admin credentials:
 *   PLAYWRIGHT_NO_WEBSERVER=1 PLAYWRIGHT_BASE_URL=http://aria.localhost \
 *   E2E_TEST_USER=admin@aria.local E2E_TEST_PASS=... npx playwright test admin-flow
 */
const USER = process.env.E2E_TEST_USER;
const PASS = process.env.E2E_TEST_PASS;

test.describe("Admin UI flows", () => {
  test.skip(!USER || !PASS, "set E2E_TEST_USER / E2E_TEST_PASS (+ Keycloak up) to run");

  test.beforeEach(async ({ page }) => {
    // Login with Keycloak
    await page.goto("/");
    const loginButton = page.getByRole("button", { name: /login with keycloak/i });
    await expect(loginButton).toBeVisible();
    await loginButton.click();
    
    await page.waitForURL(/openid-connect\/auth/i);
    await page.fill("#username", USER!);
    await page.fill("#password", PASS!);
    await page.click("#kc-login, input[type=submit], button[type=submit]");
    
    // Wait for auth to complete
    await page.waitForURL((u) => !/openid-connect/.test(u.toString()));
  });

  test("Agent Memory page loads and shows filter buttons", async ({ page }) => {
    await page.goto("/admin/memory");
    
    // Page title
    await expect(page.getByRole("heading", { name: /agent memory/i })).toBeVisible();
    
    // Filter buttons
    await expect(page.getByRole("button", { name: /^all$/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /^user$/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /^team$/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /^cache$/i })).toBeVisible();
    
    // Cleanup button
    await expect(page.getByRole("button", { name: /cleanup expired/i })).toBeVisible();
  });

  test("Agent Memory filter buttons work", async ({ page }) => {
    await page.goto("/admin/memory");
    
    // Click User filter
    await page.getByRole("button", { name: /^user$/i }).click();
    await expect(page.getByRole("button", { name: /^user$/i })).toHaveClass(/bg-blue-50/);
    
    // Click Team filter
    await page.getByRole("button", { name: /^team$/i }).click();
    await expect(page.getByRole("button", { name: /^team$/i })).toHaveClass(/bg-blue-50/);
    
    // Click All filter
    await page.getByRole("button", { name: /^all$/i }).click();
    await expect(page.getByRole("button", { name: /^all$/i })).toHaveClass(/bg-blue-50/);
  });

  test("Team Memory page loads with CRUD form", async ({ page }) => {
    await page.goto("/admin/team-memory");
    
    // Page title
    await expect(page.getByRole("heading", { name: /team conventions/i })).toBeVisible();
    
    // Add button
    await expect(page.getByRole("button", { name: /add convention/i })).toBeVisible();
  });

  test("Team Memory can open add form", async ({ page }) => {
    await page.goto("/admin/team-memory");
    
    // Click Add Convention
    await page.getByRole("button", { name: /add convention/i }).click();
    
    // Form should appear with textarea
    await expect(page.locator("textarea")).toBeVisible();
    
    // Save and Cancel buttons
    await expect(page.getByRole("button", { name: /save/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /cancel/i })).toBeVisible();
  });

  test("Tenant Config page loads with form fields", async ({ page }) => {
    await page.goto("/admin/tenant-config");
    
    // Page title
    await expect(page.getByRole("heading", { name: /tenant configuration/i })).toBeVisible();
    
    // Form fields
    await expect(page.getByText(/daily token limit/i)).toBeVisible();
    await expect(page.getByText(/max row limit/i)).toBeVisible();
    
    // Input fields should be present
    const inputs = page.locator("input[type='number']");
    await expect(inputs).toHaveCount(2);
    
    // Save button (disabled when no changes)
    await expect(page.getByRole("button", { name: /save configuration/i })).toBeVisible();
  });

  test("Tenant Config save button enables on change", async ({ page }) => {
    await page.goto("/admin/tenant-config");
    
    // Wait for data to load
    await page.waitForLoadState("networkidle");
    
    // Get the first input (token limit) and change it
    const tokenInput = page.locator("input[type='number']").first();
    const originalValue = await tokenInput.inputValue();
    
    // Clear and type new value
    await tokenInput.fill(String(Number(originalValue) + 1000));
    
    // Save button should now be enabled (not have cursor-not-allowed)
    const saveButton = page.getByRole("button", { name: /save configuration/i });
    await expect(saveButton).not.toHaveClass(/cursor-not-allowed/);
    
    // Unsaved changes indicator
    await expect(page.getByText(/unsaved changes/i)).toBeVisible();
  });

  test("Admin sidebar navigation works", async ({ page }) => {
    await page.goto("/admin");
    
    // Navigate to Agent Memory
    await page.getByRole("link", { name: /agent memory/i }).click();
    await expect(page).toHaveURL(/\/admin\/memory/);
    
    // Navigate to Team Conventions
    await page.getByRole("link", { name: /team conventions/i }).click();
    await expect(page).toHaveURL(/\/admin\/team-memory/);
    
    // Navigate to Tenant Config
    await page.getByRole("link", { name: /tenant config/i }).click();
    await expect(page).toHaveURL(/\/admin\/tenant-config/);
  });
});
