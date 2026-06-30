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
    setMatchMedia(true);
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
