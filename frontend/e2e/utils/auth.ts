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
          // `roles: ["admin"]` is required by <AdminGuard> and the admin pages'
          // `isAdmin` check; without it the app redirects away from /admin/*.
          user: { name: "Admin", email: "admin@aria.localhost", roles: ["admin"], role: "admin" },
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

    // The dashboard ("/") fetches GET /api/dashboard then awaits
    // fetchConversations() (GET /api/conversations) BEFORE rendering, so both
    // must be stubbed or the page stays stuck on "Loading dashboard...".
    await page.route('**/api/dashboard**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          stats: [
            { label: "Total Queries", value: "12.4K", change: "+14%", changeType: "up" },
            { label: "Accuracy", value: "94.2%", change: "+2.1%", changeType: "up" },
            { label: "Avg Response", value: "1.8s", change: "-0.3s", changeType: "down" },
            { label: "Active Users", value: "342", change: "+8%", changeType: "up" },
          ],
          recentConversations: [],
          savedQueries: [],
          chartData: [{ month: "Jan", revenue: 2400 }, { month: "Feb", revenue: 1398 }],
          chartConfig: { type: "bar", xKey: "month", yKeys: ["revenue"], title: "Monthly Revenue" },
        })
      });
    });

    await page.route('**/api/conversations**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    });

    await use(page);
  }
});

export { expect } from '@playwright/test';
