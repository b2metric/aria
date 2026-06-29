import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Skeleton } from "@/components/ui/skeleton";

describe("Skeleton", () => {
  it("renders a pulsing, aria-hidden placeholder and merges className", () => {
    const { container } = render(<Skeleton className="h-24 w-full" />);
    const el = container.firstChild as HTMLElement;
    expect(el).toBeTruthy();
    expect(el.className).toContain("animate-pulse");
    expect(el.className).toContain("h-24");
    expect(el.getAttribute("aria-hidden")).toBe("true");
  });
});
