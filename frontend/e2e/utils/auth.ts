import { test as base } from '@playwright/test';

export const test = base.extend({
  page: async ({ page, baseURL }, use) => {
    // 1. StorageState (Cookie injection) is standard but tricky for encrypted next-auth.
    // Instead of mocking the network exactly, we will force a mock NEXTAUTH_SESSION cookie
    // or just rely on network route matching exactly what NextAuth uses.
    
    await page.route('**/api/auth/session', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          user: { name: "Admin", email: "admin@aria.localhost" },
          accessToken: "mock-valid-token",
          expires: new Date(Date.now() + 1000 * 60 * 60 * 24).toISOString()
        })
      });
    });

    // Handle any internal providers request so NextAuth client side doesn't break
    await page.route('**/api/auth/providers', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          keycloak: { id: "keycloak", name: "Keycloak", type: "oauth", signinUrl: "mock" }
        })
      });
    });

    // 2. Intercept backend API
    await page.route('**/api/workspaces/vault/tables**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { table_name: "DIM_PREP_PRODUCTS", description: "Products", business_name: "Products" }
        ])
      });
    });

    await use(page);
  }
});

export { expect } from '@playwright/test';
