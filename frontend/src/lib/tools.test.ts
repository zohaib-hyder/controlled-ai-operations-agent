import { expect, it } from "vitest";
import { argumentsFor, ToolDescription } from "./tools";
const tool: ToolDescription = {
  name: "fixture",
  version: "1.0",
  description: "Test contract",
  required_permission: "customer:read",
  classification: "read",
  timeout_seconds: 2,
  max_result_bytes: 16384,
  output_schema: {},
  input_schema: {
    properties: {
      customer_id: { type: "string", format: "uuid" },
      limit: { type: "integer", minimum: 1, maximum: 20, default: 10 },
    },
  },
};
it("validates UUIDs before dispatch", () => {
  expect(() => argumentsFor(tool, { customer_id: "not-a-uuid" })).toThrow(
    "valid UUID",
  );
});
it("bounds numeric input without coercing decimals", () => {
  expect(() =>
    argumentsFor(tool, {
      customer_id: "00000000-0000-0000-0000-000000000000",
      limit: "2.5",
    }),
  ).toThrow("integer");
  expect(() =>
    argumentsFor(tool, {
      customer_id: "00000000-0000-0000-0000-000000000000",
      limit: "21",
    }),
  ).toThrow("permitted range");
});
it("constructs only declared fields with typed defaults", () => {
  expect(
    argumentsFor(tool, {
      customer_id: "00000000-0000-0000-0000-000000000000",
      tenant_id: "forged",
    }),
  ).toEqual({ customer_id: "00000000-0000-0000-0000-000000000000", limit: 10 });
});
