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
    // Note: getByText(/admin/i) would find multiple matches because "Ada Admin"
    // (name) also contains "admin". Use getAllByText to assert role text is present.
    expect(screen.getAllByText(/admin/i).some(el => el.textContent === "admin")).toBe(true);
    expect(container.querySelector("input")).toBeNull();
    expect(container.querySelector("button")).toBeNull();
  });
});
