# Settings Personalization & Admin Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/settings` a personal area (read-only profile + theme preference) and move all workspace-administration (Team/DB/Encryption) into the guarded `/admin` panel, deduplicating against existing admin pages.

**Architecture:** Frontend-only Next.js (App Router) reorganization. A shared theme module persists the dark-mode preference to both `localStorage` and a cookie (per-browser). Encryption UI relocates verbatim from `/settings/encryption` to `/admin/encryption` (inherits `AdminGuard`). Team & Database settings pages are deleted because `/admin/users` and `/admin/tenant-config` already cover them. No backend changes.

**Tech Stack:** Next.js 16 App Router, React, TypeScript, Tailwind, next-auth (Keycloak), lucide-react. Tests: Vitest + @testing-library/react (jsdom). E2E: Playwright.

---

## File Structure

**Create:**
- `frontend/src/lib/theme.ts` — client theme preference API (`ThemePreference`, `getThemePreference`, `setThemePreference`).
- `frontend/src/lib/theme-script.ts` — exported `THEME_INIT_SCRIPT` string (no-flicker `<head>` resolver: localStorage → cookie → prefers-color-scheme).
- `frontend/src/app/settings/profile/page.tsx` — read-only profile (name, email, role).
- `frontend/src/app/settings/appearance/page.tsx` — theme preference control (Light/Dark/System).
- `frontend/src/app/admin/encryption/page.tsx` — relocated CMEK page.
- Tests: `frontend/src/lib/__tests__/theme.test.ts`, `frontend/src/lib/__tests__/theme-script.test.ts`, `frontend/src/components/__tests__/ThemeToggle.test.tsx`, `frontend/src/app/settings/profile/__tests__/page.test.tsx`, `frontend/src/app/settings/appearance/__tests__/page.test.tsx`, `frontend/src/app/admin/encryption/__tests__/page.test.tsx`.

**Modify:**
- `frontend/src/components/ThemeToggle.tsx` — use shared `setThemePreference` (writes cookie too).
- `frontend/src/app/layout.tsx` — use `THEME_INIT_SCRIPT`.
- `frontend/src/app/settings/page.tsx` — redirect `/settings` → `/settings/profile`.
- `frontend/src/app/settings/layout.tsx` — sidebar reduced to Profile + Appearance.
- `frontend/src/app/admin/layout.tsx` — add Encryption nav item.
- `frontend/e2e/docs-screenshots.spec.ts` — update authenticated route inventory.

**Delete:**
- `frontend/src/app/settings/team/page.tsx`
- `frontend/src/app/settings/database/page.tsx`
- `frontend/src/app/settings/encryption/page.tsx`
- `frontend/src/app/settings/general/page.tsx`

---

## Task 1: Shared theme module (`lib/theme.ts`)

**Files:**
- Create: `frontend/src/lib/theme.ts`
- Test: `frontend/src/lib/__tests__/theme.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/__tests__/theme.test.ts`:

```ts
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { getThemePreference, setThemePreference, THEME_KEY } from "@/lib/theme";

function setMatchMedia(matches: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
}

describe("theme preference", () => {
  beforeEach(() => {
    localStorage.clear();
    document.cookie = `${THEME_KEY}=; path=/; max-age=0`;
    document.documentElement.removeAttribute("data-theme");
    setMatchMedia(false);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("persists an explicit choice to data-theme, localStorage and cookie", () => {
    setThemePreference("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(localStorage.getItem(THEME_KEY)).toBe("dark");
    expect(document.cookie).toContain(`${THEME_KEY}=dark`);
  });

  it("'system' clears storage and resolves data-theme from prefers-color-scheme", () => {
    setThemePreference("dark");
    setMatchMedia(true); // system prefers dark
    setThemePreference("system");
    expect(localStorage.getItem(THEME_KEY)).toBeNull();
    expect(document.cookie).not.toContain(`${THEME_KEY}=dark`);
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("reads back an explicit preference, defaulting to 'system'", () => {
    expect(getThemePreference()).toBe("system");
    setThemePreference("light");
    expect(getThemePreference()).toBe("light");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/__tests__/theme.test.ts`
Expected: FAIL — cannot resolve `@/lib/theme`.

- [ ] **Step 3: Write minimal implementation**

Create `frontend/src/lib/theme.ts`:

```ts
// Client-side theme preference. Persisted to BOTH localStorage and a cookie so
// the choice survives reloads (localStorage = fast path) and is SSR-readable
// (cookie). "system" stores nothing and follows prefers-color-scheme.

export type ThemePreference = "light" | "dark" | "system";

export const THEME_KEY = "theme";
const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;

function resolve(pref: ThemePreference): "light" | "dark" {
  if (pref !== "system") return pref;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** Apply a preference now and persist it (or clear it, for "system"). */
export function setThemePreference(pref: ThemePreference): void {
  if (typeof document === "undefined") return;
  document.documentElement.setAttribute("data-theme", resolve(pref));
  try {
    if (pref === "system") {
      localStorage.removeItem(THEME_KEY);
      document.cookie = `${THEME_KEY}=; path=/; max-age=0; samesite=lax`;
    } else {
      localStorage.setItem(THEME_KEY, pref);
      document.cookie = `${THEME_KEY}=${pref}; path=/; max-age=${ONE_YEAR_SECONDS}; samesite=lax`;
    }
  } catch {
    // storage/cookies may be unavailable (private mode) — theme still applies for the session
  }
}

/** Read the stored explicit preference, or "system" when none is set. */
export function getThemePreference(): ThemePreference {
  if (typeof document === "undefined") return "system";
  try {
    const v = localStorage.getItem(THEME_KEY);
    if (v === "light" || v === "dark") return v;
  } catch {
    // ignore
  }
  return "system";
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/__tests__/theme.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/theme.ts frontend/src/lib/__tests__/theme.test.ts
git commit -m "feat(frontend): shared theme preference module (localStorage + cookie)"
```

---

## Task 2: No-flicker init script (`lib/theme-script.ts`)

**Files:**
- Create: `frontend/src/lib/theme-script.ts`
- Test: `frontend/src/lib/__tests__/theme-script.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/__tests__/theme-script.test.ts`:

```ts
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { THEME_INIT_SCRIPT } from "@/lib/theme-script";

function setMatchMedia(matches: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches, media: query, addEventListener: () => {}, removeEventListener: () => {},
  }));
}

describe("THEME_INIT_SCRIPT", () => {
  beforeEach(() => {
    localStorage.clear();
    document.cookie = "theme=; path=/; max-age=0";
    document.documentElement.removeAttribute("data-theme");
    setMatchMedia(false);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("prefers localStorage", () => {
    localStorage.setItem("theme", "dark");
    // eslint-disable-next-line no-eval
    eval(THEME_INIT_SCRIPT);
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("falls back to the cookie when localStorage is empty", () => {
    document.cookie = "theme=dark; path=/";
    // eslint-disable-next-line no-eval
    eval(THEME_INIT_SCRIPT);
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("falls back to prefers-color-scheme when nothing is stored", () => {
    setMatchMedia(true);
    // eslint-disable-next-line no-eval
    eval(THEME_INIT_SCRIPT);
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/__tests__/theme-script.test.ts`
Expected: FAIL — cannot resolve `@/lib/theme-script`.

- [ ] **Step 3: Write minimal implementation**

Create `frontend/src/lib/theme-script.ts`:

```ts
// Synchronous <head> script string. Runs before paint to set data-theme and
// avoid a flash of the wrong theme. Resolution order: localStorage → cookie →
// prefers-color-scheme. Keep this dependency-free (it is injected as raw text).
export const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem('theme');if(!t){var m=document.cookie.match(/(?:^|; )theme=([^;]+)/);if(m){t=decodeURIComponent(m[1]);}}if(t!=='dark'&&t!=='light'){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/__tests__/theme-script.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/theme-script.ts frontend/src/lib/__tests__/theme-script.test.ts
git commit -m "feat(frontend): cookie-aware no-flicker theme init script"
```

---

## Task 3: Wire the init script into the root layout

**Files:**
- Modify: `frontend/src/app/layout.tsx:24-36`

- [ ] **Step 1: Replace the inline script constant and usage**

In `frontend/src/app/layout.tsx`, add the import near the top (after line 5 `import { Sidebar }`):

```tsx
import { THEME_INIT_SCRIPT } from "@/lib/theme-script";
```

Delete the `themeScript` constant (lines 24-26):

```tsx
// Applies the saved (or system) theme before paint to avoid a flash of the
// wrong theme on load. Runs synchronously in <head> ahead of hydration.
const themeScript = `(function(){try{var t=localStorage.getItem('theme');if(!t){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`;
```

Change the `<script>` usage (line 36) from:

```tsx
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
```

to:

```tsx
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
```

- [ ] **Step 2: Verify the build/types still compile**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors referencing `layout.tsx`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/layout.tsx
git commit -m "refactor(frontend): root layout uses shared theme init script"
```

---

## Task 4: ThemeToggle uses the shared module (writes cookie)

**Files:**
- Modify: `frontend/src/components/ThemeToggle.tsx:23-32`
- Test: `frontend/src/components/__tests__/ThemeToggle.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/__tests__/ThemeToggle.test.tsx`:

```tsx
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeToggle } from "@/components/ThemeToggle";

describe("ThemeToggle", () => {
  beforeEach(() => {
    localStorage.clear();
    document.cookie = "theme=; path=/; max-age=0";
    document.documentElement.setAttribute("data-theme", "light");
  });

  it("toggling to dark persists to localStorage AND a cookie", async () => {
    render(<ThemeToggle />);
    await userEvent.click(screen.getByRole("button"));
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(localStorage.getItem("theme")).toBe("dark");
    expect(document.cookie).toContain("theme=dark");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/__tests__/ThemeToggle.test.tsx`
Expected: FAIL — cookie does not contain `theme=dark` (current toggle only writes localStorage).

- [ ] **Step 3: Update the implementation**

In `frontend/src/components/ThemeToggle.tsx`, add the import after line 4 (`import { Moon, Sun }`):

```tsx
import { setThemePreference } from "@/lib/theme";
```

Replace the `toggle` function (lines 23-32) with:

```tsx
  const toggle = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    setThemePreference(next);
  };
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/__tests__/ThemeToggle.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ThemeToggle.tsx frontend/src/components/__tests__/ThemeToggle.test.tsx
git commit -m "feat(frontend): ThemeToggle persists theme to cookie via shared module"
```

---

## Task 5: Appearance settings page

**Files:**
- Create: `frontend/src/app/settings/appearance/page.tsx`
- Test: `frontend/src/app/settings/appearance/__tests__/page.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/app/settings/appearance/__tests__/page.test.tsx`:

```tsx
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AppearanceSettings from "../page";

describe("AppearanceSettings", () => {
  beforeEach(() => {
    localStorage.clear();
    document.cookie = "theme=; path=/; max-age=0";
    document.documentElement.setAttribute("data-theme", "light");
  });

  it("offers Light / Dark / System and applies + persists the chosen one", async () => {
    render(<AppearanceSettings />);
    await userEvent.click(screen.getByRole("button", { name: /dark/i }));
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(localStorage.getItem("theme")).toBe("dark");
    expect(document.cookie).toContain("theme=dark");
    // the active option is marked pressed
    expect(screen.getByRole("button", { name: /dark/i })).toHaveAttribute("aria-pressed", "true");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/app/settings/appearance/__tests__/page.test.tsx`
Expected: FAIL — cannot resolve `../page`.

- [ ] **Step 3: Write the implementation**

Create `frontend/src/app/settings/appearance/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { Sun, Moon, Monitor } from "lucide-react";
import { getThemePreference, setThemePreference, type ThemePreference } from "@/lib/theme";

const OPTIONS: { value: ThemePreference; label: string; Icon: typeof Sun }[] = [
  { value: "light", label: "Light", Icon: Sun },
  { value: "dark", label: "Dark", Icon: Moon },
  { value: "system", label: "System", Icon: Monitor },
];

export default function AppearanceSettings() {
  const [pref, setPref] = useState<ThemePreference>("system");

  // Sync from the value the no-flicker inline script already applied.
  useEffect(() => setPref(getThemePreference()), []);

  const choose = (value: ThemePreference) => {
    setPref(value);
    setThemePreference(value);
  };

  return (
    <div className="max-w-2xl mx-auto py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Appearance</h1>
        <p className="text-gray-500 mt-1">Choose how ARIA looks on this browser.</p>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="text-sm font-medium text-gray-700 mb-3">Theme</div>
        <div className="grid grid-cols-3 gap-3">
          {OPTIONS.map(({ value, label, Icon }) => {
            const active = pref === value;
            return (
              <button
                key={value}
                type="button"
                aria-pressed={active}
                onClick={() => choose(value)}
                className={`flex flex-col items-center justify-center gap-2 rounded-lg border px-4 py-5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                  active
                    ? "border-blue-600 bg-blue-50 text-blue-700"
                    : "border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                }`}
              >
                <Icon className="h-5 w-5" />
                {label}
              </button>
            );
          })}
        </div>
        <p className="mt-3 text-xs text-gray-500">
          This preference is stored in your browser. &quot;System&quot; follows your OS setting.
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/app/settings/appearance/__tests__/page.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/settings/appearance/page.tsx frontend/src/app/settings/appearance/__tests__/page.test.tsx
git commit -m "feat(frontend): Appearance settings page (Light/Dark/System)"
```

---

## Task 6: Profile settings page (read-only)

**Files:**
- Create: `frontend/src/app/settings/profile/page.tsx`
- Test: `frontend/src/app/settings/profile/__tests__/page.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/app/settings/profile/__tests__/page.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { useSession } from "next-auth/react";
import ProfileSettings from "../page";

vi.mock("next-auth/react", () => ({ useSession: vi.fn() }));

describe("ProfileSettings", () => {
  beforeEach(() => {
    (useSession as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { user: { name: "Ada Admin", email: "ada@aria.local", roles: ["admin"] } },
      status: "authenticated",
    });
  });

  it("shows the session name, email and role read-only (no edit controls)", () => {
    const { container } = render(<ProfileSettings />);
    expect(screen.getByText("Ada Admin")).toBeTruthy();
    expect(screen.getByText("ada@aria.local")).toBeTruthy();
    expect(screen.getByText(/admin/i)).toBeTruthy();
    // read-only: no form inputs or submit buttons
    expect(container.querySelector("input")).toBeNull();
    expect(container.querySelector("button")).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/app/settings/profile/__tests__/page.test.tsx`
Expected: FAIL — cannot resolve `../page`.

- [ ] **Step 3: Write the implementation**

Create `frontend/src/app/settings/profile/page.tsx`:

```tsx
"use client";

import { useSession } from "next-auth/react";
import { User, Mail, Shield } from "lucide-react";

interface ProfileRowProps {
  Icon: typeof User;
  label: string;
  value: string;
}

function ProfileRow({ Icon, label, value }: ProfileRowProps) {
  return (
    <div className="flex items-center gap-4 px-6 py-4">
      <Icon className="h-5 w-5 text-gray-400 flex-shrink-0" />
      <div className="min-w-0">
        <div className="text-xs uppercase tracking-wider text-gray-400">{label}</div>
        <div className="text-sm font-medium text-gray-900 break-all">{value}</div>
      </div>
    </div>
  );
}

export default function ProfileSettings() {
  const { data: session } = useSession();
  const user = session?.user;
  const roles = (user as { roles?: string[] } | undefined)?.roles ?? [];

  const name = user?.name || "—";
  const email = user?.email || "—";
  const roleLabel = roles.length ? roles.join(", ") : "—";

  return (
    <div className="max-w-2xl mx-auto py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Profile</h1>
        <p className="text-gray-500 mt-1">Your account details.</p>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-100 overflow-hidden">
        <ProfileRow Icon={User} label="Name" value={name} />
        <ProfileRow Icon={Mail} label="Email" value={email} />
        <ProfileRow Icon={Shield} label="Role" value={roleLabel} />
      </div>

      <p className="text-xs text-gray-500">
        Password and email changes are managed by your administrator.
      </p>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/app/settings/profile/__tests__/page.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/settings/profile/page.tsx frontend/src/app/settings/profile/__tests__/page.test.tsx
git commit -m "feat(frontend): read-only profile settings page"
```

---

## Task 7: Redirect `/settings` → `/settings/profile`

**Files:**
- Modify: `frontend/src/app/settings/page.tsx:1-6`

- [ ] **Step 1: Replace the redirect target**

Replace the entire contents of `frontend/src/app/settings/page.tsx` with:

```tsx
import { redirect } from "next/navigation";

export default function SettingsPage() {
  // /settings is personal now; land on the profile screen.
  redirect("/settings/profile");
}
```

- [ ] **Step 2: Verify types compile**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors referencing `settings/page.tsx`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/settings/page.tsx
git commit -m "refactor(frontend): /settings lands on profile"
```

---

## Task 8: Settings sidebar → Profile + Appearance only

**Files:**
- Modify: `frontend/src/app/settings/layout.tsx` (full replace)

- [ ] **Step 1: Replace the file contents**

Replace the entire contents of `frontend/src/app/settings/layout.tsx` with:

```tsx
"use client";

import { ReactNode, useState } from "react";
import Link from "next/link";
import { User, Palette, ChevronLeft, ChevronRight, LayoutDashboard } from "lucide-react";
import { usePathname } from "next/navigation";

const NAV: { href: string; label: string; Icon: typeof User }[] = [
  { href: "/settings/profile", label: "Profile", Icon: User },
  { href: "/settings/appearance", label: "Appearance", Icon: Palette },
];

export default function SettingsLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900">
      <aside
        className={`bg-white p-6 flex flex-col border-r border-gray-200 relative transition-all duration-300 ease-in-out
          ${isCollapsed ? "w-24" : "w-64"}
        `}
      >
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="absolute -right-3 top-6 bg-white border border-gray-200 rounded-full p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-50 transition-colors z-10 hidden md:block shadow-sm"
          title={isCollapsed ? "Expand menu" : "Collapse menu"}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>

        <div className={`flex items-center mb-8 transition-all duration-300 ${isCollapsed ? "justify-center gap-0" : "justify-start gap-2"}`}>
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
            <span className="text-[#ffffff] font-bold text-xl">A</span>
          </div>
          {!isCollapsed && (
            <span className="font-bold text-xl tracking-wide text-gray-900 whitespace-nowrap overflow-hidden transition-opacity duration-300">
              Settings
            </span>
          )}
        </div>

        <nav className="flex-1 space-y-1 overflow-x-hidden">
          <Link
            href="/"
            className={`flex items-center p-3 rounded-lg transition-colors whitespace-nowrap text-gray-600 hover:bg-gray-100 hover:text-gray-900 ${isCollapsed ? "justify-center" : "justify-start"}`}
            title={isCollapsed ? "Back to Dashboard" : undefined}
          >
            <LayoutDashboard className={`w-5 h-5 flex-shrink-0 ${isCollapsed ? "" : "mr-3"} text-gray-500`} />
            {!isCollapsed && <span className="font-medium">Back to App</span>}
          </Link>

          <div className="pt-4 pb-2">
            <div className={`text-xs font-semibold text-gray-400 uppercase tracking-wider ${isCollapsed ? "text-center" : "px-3"}`}>
              {isCollapsed ? "---" : "Account"}
            </div>
          </div>

          {NAV.map(({ href, label, Icon }) => (
            <Link
              key={href}
              href={href}
              className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
                ${isCollapsed ? "justify-center" : "justify-start gap-3"}
                ${pathname?.includes(href) ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
              `}
              title={label}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">{label}</span>}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="flex-1 p-8 overflow-y-auto w-full transition-all duration-300">
        {children}
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Verify types compile**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors referencing `settings/layout.tsx`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/settings/layout.tsx
git commit -m "feat(frontend): settings sidebar is personal (Profile + Appearance)"
```

---

## Task 9: Relocate Encryption to `/admin/encryption`

**Files:**
- Create: `frontend/src/app/admin/encryption/page.tsx`
- Test: `frontend/src/app/admin/encryption/__tests__/page.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/app/admin/encryption/__tests__/page.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { useSession } from "next-auth/react";
import EncryptionSettings from "../page";

vi.mock("next-auth/react", () => ({ useSession: vi.fn() }));

describe("admin EncryptionSettings", () => {
  beforeEach(() => {
    (useSession as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { accessToken: "tok", user: { roles: ["admin"] } },
      status: "authenticated",
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => ({
        ok: true,
        json: async () =>
          String(url).includes("/encryption/status")
            ? { provider: "app", key_uri: null, is_active: true, reachable: true }
            : { data: [] },
      })),
    );
  });

  it("renders the CMEK heading and probes the encryption status endpoint", async () => {
    render(<EncryptionSettings />);
    await waitFor(() => expect(screen.getByText(/Encryption \(CMEK\)/i)).toBeTruthy());
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/admin/encryption/status"),
      expect.anything(),
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/app/admin/encryption/__tests__/page.test.tsx`
Expected: FAIL — cannot resolve `../page`.

- [ ] **Step 3: Create the page by copying the existing encryption page verbatim**

Run:

```bash
mkdir -p frontend/src/app/admin/encryption
cp frontend/src/app/settings/encryption/page.tsx frontend/src/app/admin/encryption/page.tsx
```

The file content is identical to the current `settings/encryption/page.tsx` (default export `EncryptionSettings`, calls `GET /api/admin/encryption/status`, `GET /api/admin/audit-logs`, `PATCH /api/admin/encryption`, `POST /api/admin/encryption/rotate`). No code change is needed — it already targets `/api/admin/*` endpoints.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/app/admin/encryption/__tests__/page.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/admin/encryption/page.tsx frontend/src/app/admin/encryption/__tests__/page.test.tsx
git commit -m "feat(frontend): relocate Encryption (CMEK) page under guarded /admin"
```

---

## Task 10: Add Encryption nav item to the admin sidebar

**Files:**
- Modify: `frontend/src/app/admin/layout.tsx:5` (import) and `:114` (insert nav link after Tenant Config)

- [ ] **Step 1: Add the `KeyRound` icon import**

In `frontend/src/app/admin/layout.tsx` line 5, append `KeyRound` to the lucide-react import list:

```tsx
import { Database, Settings, ShieldAlert, ChevronLeft, ChevronRight, Users, Brain, Lock, LayoutDashboard, Activity, Cpu, Link2, MessagesSquare, Boxes, BookOpen, KeyRound } from "lucide-react";
```

- [ ] **Step 2: Insert the Encryption link directly after the Tenant Config `</Link>` (after line 114)**

Immediately after the Tenant Config link block (the `</Link>` on line 114, before the LLM Config `<Link>` on line 115), insert:

```tsx
            <Link
              href="/admin/encryption"
              className={`flex items-center px-3 py-2.5 rounded-lg transition-colors whitespace-nowrap
                ${isCollapsed ? "justify-center" : "justify-start gap-3"}
                ${pathname?.includes("/admin/encryption") ? "bg-blue-50 text-blue-700" : "text-gray-600 hover:bg-blue-50 hover:text-blue-700"}
              `}
              title="Encryption (CMEK)"
            >
              <KeyRound className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span className="text-sm font-medium transition-opacity duration-300">Encryption</span>}
            </Link>
```

- [ ] **Step 3: Verify types compile**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors referencing `admin/layout.tsx`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/admin/layout.tsx
git commit -m "feat(frontend): admin sidebar gains Encryption nav item"
```

---

## Task 11: Delete the relocated/duplicated settings pages

**Files:**
- Delete: `frontend/src/app/settings/team/page.tsx`, `frontend/src/app/settings/database/page.tsx`, `frontend/src/app/settings/encryption/page.tsx`, `frontend/src/app/settings/general/page.tsx`

- [ ] **Step 1: Remove the page files**

Run:

```bash
git rm frontend/src/app/settings/team/page.tsx \
       frontend/src/app/settings/database/page.tsx \
       frontend/src/app/settings/encryption/page.tsx \
       frontend/src/app/settings/general/page.tsx
```

- [ ] **Step 2: Confirm nothing imports the deleted pages**

Run:

```bash
cd frontend && grep -rn -E "settings/(team|database|encryption|general)" src
```

Expected: no matches (the sidebar links were removed in Task 8; the redirect was updated in Task 7).

- [ ] **Step 3: Verify the app still type-checks**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore(frontend): remove team/database/encryption/general settings pages (moved to admin or personal)"
```

---

## Task 12: Update the Academy screenshot inventory (E2E)

**Files:**
- Modify: `frontend/e2e/docs-screenshots.spec.ts:19-41`

- [ ] **Step 1: Replace the obsolete settings rows in the `AUTHED` array**

In `frontend/e2e/docs-screenshots.spec.ts`, replace these lines:

```ts
  { name: "settings", path: "/settings" },
  { name: "settings-general", path: "/settings/general" },
  { name: "settings-team", path: "/settings/team" },
  { name: "settings-database", path: "/settings/database" },
  { name: "settings-encryption", path: "/settings/encryption" },
```

with:

```ts
  { name: "settings", path: "/settings" },
  { name: "settings-profile", path: "/settings/profile" },
  { name: "settings-appearance", path: "/settings/appearance" },
```

- [ ] **Step 2: Add an `admin-encryption` row after `admin-tenant-config`**

Immediately after the line:

```ts
  { name: "admin-tenant-config", path: "/admin/tenant-config" },
```

insert:

```ts
  { name: "admin-encryption", path: "/admin/encryption" },
```

- [ ] **Step 3: Commit**

```bash
git add frontend/e2e/docs-screenshots.spec.ts
git commit -m "test(frontend): update Academy screenshot routes for settings/admin reorg"
```

---

## Task 13: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full frontend unit suite**

Run: `cd frontend && npx vitest run`
Expected: all tests PASS (including the new theme, theme-script, ThemeToggle, profile, appearance, admin/encryption tests). Fix any regression before continuing.

- [ ] **Step 2: Type-check the whole frontend**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Production build**

Run: `cd frontend && npm run build`
Expected: build succeeds; `/settings/profile`, `/settings/appearance`, `/admin/encryption` appear in the route manifest; `/settings/team`, `/settings/database`, `/settings/encryption`, `/settings/general` do not.

- [ ] **Step 4: Visual smoke (per CLAUDE.md — FE is not optional)**

With the dev stack running, drive `aria.localhost` with Playwright/Chrome MCP and screenshot:
- `/settings` → redirects to `/settings/profile` (name/email/role visible, no inputs).
- `/settings/appearance` → toggling Dark flips the theme and survives a reload (cookie/localStorage).
- `/admin/encryption` → CMEK page renders under the admin shell; sidebar shows Encryption highlighted.
- Confirm the `/settings` sidebar no longer lists Team/Database/Encryption.

Capture before/after screenshots as run-evidence.

- [ ] **Step 5: Final commit (if visual fixes were needed)**

```bash
git add -A
git commit -m "fix(frontend): settings/admin reorg visual polish"
```

---

## Self-Review Notes

- **Spec coverage:** A (personal settings) → Tasks 5-8; B (admin encryption) → Tasks 9-10; C (dedupe/delete) → Task 11; D (cookie+localStorage theme) → Tasks 1-4; E (nav/RBAC) → Tasks 8,10,11; F (no backend changes) → confirmed, no backend task; Testing → tests embedded per task + Task 13.
- **Same-PR constraint:** Task 9 (create `/admin/encryption`) precedes Task 11 (delete `/settings/encryption`) within this single plan/branch, so the encryption endpoints are never frontend-dark.
- **Scope note:** Profile shows name/email/role only — `team` is not present in the NextAuth session (would require a backend call) and is intentionally out of scope for this read-only phase.
- **Type consistency:** `ThemePreference = "light" | "dark" | "system"` and `setThemePreference`/`getThemePreference`/`THEME_KEY` are used identically across Tasks 1, 4, 5; `THEME_INIT_SCRIPT` across Tasks 2-3.
