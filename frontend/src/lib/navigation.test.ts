import { describe, it, expect } from "vitest";
import { navigation, visibleNavigation, permittedPath } from "./navigation";
describe("permission-aware workspace navigation", () => {
  it("provides unique destinations", () => {
    expect(new Set(navigation.map((item) => item.href)).size).toBe(
      navigation.length,
    );
  });
  it("hides privileged areas from operators", () => {
    const visible = visibleNavigation([
      "customer:read",
      "account:read",
      "ticket:read",
      "investigation:create",
    ]);
    expect(visible.map((item) => item.href)).toEqual([
      "/",
      "/action-proposals",
      "/operations",
      "/incidents",
      "/diagnostics",
      "/tools",
      "/investigations",
      "/customers",
      "/accounts",
      "/tickets",
    ]);
  });
  it("denies direct privileged and nested routes", () => {
    expect(permittedPath("/settings", ["customer:read"])).toBe(false);
    expect(permittedPath("/customers/fixture", ["customer:read"])).toBe(true);
    expect(permittedPath("/customers/fixture", [])).toBe(false);
  });
  it("shows reviewer approvals and auditor audit without granting write capabilities", () => {
    expect(
      visibleNavigation(["approval:review"]).some(
        (item) => item.href === "/approvals",
      ),
    ).toBe(true);
    expect(
      visibleNavigation(["audit:read"]).some(
        (item) => item.href === "/investigations",
      ),
    ).toBe(false);
  });
});
