import { expect, it } from "vitest";
import { investigationBody } from "./investigations";
const id = "00000000-0000-0000-0000-000000000000";
it("bounds goals and requires customer selection", () => {
  expect(() => investigationBody("x", id, "")).toThrow();
  expect(() => investigationBody("inspect account", "", "")).toThrow();
  expect(() => investigationBody("x".repeat(1001), id, "")).toThrow();
});
it("omits empty ticket and never supplies identity", () => {
  expect(investigationBody(" inspect account ", id, "")).toEqual({
    goal: "inspect account",
    customer_id: id,
  });
});
it("includes selected ticket reference", () => {
  expect(investigationBody("inspect account", id, id).ticket_id).toBe(id);
});
