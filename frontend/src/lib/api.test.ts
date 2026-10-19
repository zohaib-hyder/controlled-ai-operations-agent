import { afterEach, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";
afterEach(() => vi.unstubAllGlobals());
it("uses same-origin cookies and disables caching", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
  vi.stubGlobal("fetch", fetchMock);
  await expect(api("/customers")).resolves.toEqual({ ok: true });
  expect(fetchMock.mock.calls[0][1]).toMatchObject({
    credentials: "same-origin",
    cache: "no-store",
  });
});
it("preserves backend permission denial", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ error: { message: "Permission denied" } }),
          { status: 403 },
        ),
      ),
  );
  await expect(api("/customers")).rejects.toMatchObject({
    status: 403,
    message: "Permission denied",
  });
});
it("handles service errors without a structured body", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response("unavailable", { status: 503 })),
  );
  await expect(api("/auth/me", {}, false)).rejects.toBeInstanceOf(ApiError);
});
