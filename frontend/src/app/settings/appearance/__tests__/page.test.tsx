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
    expect(screen.getByRole("button", { name: /dark/i })).toHaveAttribute("aria-pressed", "true");
  });
});
