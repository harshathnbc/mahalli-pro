import type { Role } from "./auth";

export interface NavItem {
  href: string;
  labelKey: string; // key under the "nav" message namespace
  roles: Role[]; // roles allowed to see this item
}

const ALL: Role[] = [
  "MASTER_ADMIN",
  "SUPER_ADMIN",
  "COMPANY_ADMIN",
  "HR_ADMIN",
  "PROCUREMENT_ADMIN",
  "FINANCE_ADMIN",
];

// Department silos: each module is visible only to its role (+ Super/Company Admin).
const ADMIN: Role[] = ["SUPER_ADMIN", "COMPANY_ADMIN"];

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", labelKey: "overview", roles: ALL },
  { href: "/dashboard/hr", labelKey: "hr", roles: [...ADMIN, "HR_ADMIN"] },
  { href: "/dashboard/procurement", labelKey: "procurement", roles: [...ADMIN, "PROCUREMENT_ADMIN"] },
  { href: "/dashboard/finance", labelKey: "finance", roles: [...ADMIN, "FINANCE_ADMIN"] },
  { href: "/dashboard/reports", labelKey: "reports", roles: ADMIN },
  { href: "/dashboard/copilot", labelKey: "copilot", roles: ALL },
];

export function navForRole(role: Role): NavItem[] {
  return NAV_ITEMS.filter((item) => item.roles.includes(role));
}
