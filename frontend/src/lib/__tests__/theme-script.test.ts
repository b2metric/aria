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
