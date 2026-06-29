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
