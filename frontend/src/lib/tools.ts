export interface ToolDescription {
  name: string;
  version: string;
  description: string;
  required_permission: string;
  classification: "read";
  timeout_seconds: number;
  max_result_bytes: number;
  input_schema: {
    properties: Record<
      string,
      {
        type?: string;
        format?: string;
        minimum?: number;
        maximum?: number;
        maxLength?: number;
        default?: unknown;
      }
    >;
    required?: string[];
  };
  output_schema: Record<string, unknown>;
}
export interface ToolResult {
  execution_id: string;
  tool_name: string;
  tool_version: string;
  status: "success" | "error" | "cancelled";
  data: Record<string, unknown> | null;
  error: { code: string; message: string } | null;
  started_at: string;
  completed_at: string;
  duration_ms: number;
  correlation_id: string;
}
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function argumentsFor(
  tool: ToolDescription,
  values: Record<string, string>,
): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, property] of Object.entries(tool.input_schema.properties)) {
    const value = values[key] ?? String(property.default ?? "");
    if (property.format === "uuid" && !uuid.test(value))
      throw new Error(`${key} must be a valid UUID`);
    if (property.type === "integer") {
      if (!/^\d+$/.test(value)) throw new Error(`${key} must be an integer`);
      const number = Number(value);
      if (
        !Number.isSafeInteger(number) ||
        number < (property.minimum ?? 0) ||
        number > (property.maximum ?? 100)
      )
        throw new Error(`${key} is outside its permitted range`);
      result[key] = number;
    } else {
      if (!value.trim() || value.length > (property.maxLength ?? 240))
        throw new Error(`${key} is required and must fit the contract`);
      result[key] = value;
    }
  }
  return result;
}
