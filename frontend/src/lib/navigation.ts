export const navigation = [
  { href: "/", label: "Overview", icon: "◈", permission: null },
  { href: "/action-proposals", label: "Action proposals", icon: "◇", permission: "investigation:create" },
  { href: "/execution-jobs", label: "Execution jobs", icon: "◷", permission: "action:execute" },
  { href: "/operations", label: "Command Center", icon: "◈", permission: "customer:read" },
  { href: "/incidents", label: "Incidents", icon: "⚑", permission: "customer:read" },
  { href: "/diagnostics", label: "Diagnostics", icon: "⌕", permission: "customer:read" },
  { href: "/tools", label: "Tool Explorer", icon: "⌘", permission: "customer:read" },
  {
    href: "/investigations",
    label: "Investigations",
    icon: "⌕",
    permission: "investigation:create",
  },
  {
    href: "/customers",
    label: "Customers",
    icon: "▦",
    permission: "customer:read",
  },
  {
    href: "/accounts",
    label: "Accounts",
    icon: "▤",
    permission: "account:read",
  },
  { href: "/tickets", label: "Tickets", icon: "▱", permission: "ticket:read" },
  {
    href: "/approvals",
    label: "Approvals",
    icon: "◇",
    permission: "approval:review",
  },
  {
    href: "/audit",
    label: "Audit timeline",
    icon: "≡",
    permission: "audit:read",
  },
  {
    href: "/settings",
    label: "Settings",
    icon: "⚙",
    permission: "settings:manage",
  },
] as const;
export function visibleNavigation(permissions: readonly string[]) {
  return navigation.filter(
    (item) => !item.permission || permissions.includes(item.permission),
  );
}
export function permittedPath(
  path: string,
  permissions: readonly string[],
): boolean {
  const item = navigation.find(
    (item) =>
      item.href !== "/" &&
      (path === item.href || path.startsWith(`${item.href}/`)),
  );
  return !item?.permission || permissions.includes(item.permission);
}
