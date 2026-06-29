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
