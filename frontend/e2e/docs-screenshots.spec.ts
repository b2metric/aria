import { test, type Page } from "@playwright/test";
import path from "path";

// Drives the live app to capture screenshots for the end-user "Academy" docs.
// Run: PLAYWRIGHT_NO_WEBSERVER=1 PLAYWRIGHT_BASE_URL=http://aria.localhost \
//        E2E_TEST_USER=admin@aria.local E2E_TEST_PASS=12345 \
//        npx playwright test docs-screenshots
// PNGs land in docs-site/guide/_screenshots/<name>.png (consumed by guide/*.mdx).
const USER = process.env.E2E_TEST_USER || "admin@aria.local";
const PASS = process.env.E2E_TEST_PASS || "admin";
const OUT = path.resolve(__dirname, "../../docs-site/guide/_screenshots");

const PUBLIC: { name: string; path: string }[] = [
  { name: "login", path: "/login" },
  { name: "register", path: "/register" },
];
// All authenticated screens (the end-user Academy inventory).
const AUTHED: { name: string; path: string }[] = [
  { name: "dashboard", path: "/" },
  { name: "chat", path: "/chat" },
  { name: "settings", path: "/settings" },
  { name: "settings-general", path: "/settings/general" },
  { name: "settings-team", path: "/settings/team" },
  { name: "settings-database", path: "/settings/database" },
  { name: "settings-encryption", path: "/settings/encryption" },
  { name: "onboarding-database", path: "/onboarding/database" },
  { name: "onboarding-sync", path: "/onboarding/sync" },
  { name: "admin", path: "/admin" },
  { name: "admin-users", path: "/admin/users" },
  { name: "admin-health", path: "/admin/health" },
  { name: "admin-memory", path: "/admin/memory" },
  { name: "admin-team-memory", path: "/admin/team-memory" },
  { name: "admin-audit-log", path: "/admin/audit-log" },
  { name: "admin-tokens", path: "/admin/tokens" },
  { name: "admin-vault-access", path: "/admin/vault-access" },
  { name: "admin-tenant-config", path: "/admin/tenant-config" },
  { name: "admin-llm-config", path: "/admin/llm-config" },
  { name: "admin-schema", path: "/admin/schema" },
];

async function shoot(page: Page, name: string) {
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage: true });
}

test("capture Academy screenshots", async ({ page }) => {
  test.setTimeout(300000);

  for (const s of PUBLIC) {
    try { await page.goto(s.path); await shoot(page, s.name); }
    catch (e) { console.log(`[screenshot] ${s.name} failed: ${e}`); }
  }

  await page.goto("/login");
  await page.fill("input[name='email']", USER);
  await page.fill("input[name='password']", PASS);
  await page.getByRole("button", { name: /Sign in/i }).click();
  const authed = await page.waitForURL("/", { timeout: 20000 }).then(() => true).catch(() => false);

  if (!authed) {
    console.log("[screenshot] auth screens skipped — login failed (check E2E_TEST_USER/PASS).");
    return;
  }
  let ok = 0;
  for (const s of AUTHED) {
    try { await page.goto(s.path); await shoot(page, s.name); ok++; }
    catch (e) { console.log(`[screenshot] ${s.name} failed: ${e}`); }
  }
  console.log(`[screenshot] captured ${ok}/${AUTHED.length} authed screens`);
});
