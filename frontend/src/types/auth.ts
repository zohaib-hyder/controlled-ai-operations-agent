export type Role = "operator" | "reviewer" | "admin" | "auditor";
export interface CurrentUser {
  user_id: string;
  tenant_id: string;
  session_id: string;
  email: string;
  role: Role;
  permissions: string[];
}
