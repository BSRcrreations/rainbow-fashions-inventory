import type { UserRole } from "../types";

const billing: UserRole[] = ["OWNER", "MANAGER", "CASHIER", "STAFF"];
const stock: UserRole[] = ["OWNER", "MANAGER", "STOCK_STAFF", "STAFF"];
const purchasing: UserRole[] = ["OWNER", "MANAGER", "STOCK_STAFF", "ACCOUNTANT", "STAFF"];
const managers: UserRole[] = ["OWNER", "MANAGER"];
const financial: UserRole[] = ["OWNER", "MANAGER", "ACCOUNTANT", "VIEWER"];

export function routeAllowed(path: string, role: UserRole): boolean {
  if (role === "OWNER") return true;
  if (/^\/(users|settings\/security|backup-status|stock\/opening-import)/.test(path)) return false;
  if (path.startsWith("/sales/") && path.endsWith("/edit")) return managers.includes(role);
  if (["/sales", "/day-closing", "/sales/returns"].includes(path)) return billing.includes(role) || (path === "/sales/returns" && role === "MANAGER");
  if (/^\/stock(?:-|\/)adjust/.test(path)) return managers.includes(role);
  if (path === "/stock/quick" || path === "/stock/scan") return stock.includes(role);
  if (path === "/purchases/returns") return managers.includes(role);
  if (path.startsWith("/purchases")) return purchasing.includes(role) || (role === "VIEWER" && path === "/purchases");
  if (path === "/store-settings") return false;
  if (path === "/purchases/returns") return managers.includes(role);
  if (path === "/audit-log") return [...managers, "ACCOUNTANT"].includes(role);
  if (["/reports", "/expenses", "/suppliers", "/stock/integrity"].includes(path)) return financial.includes(role) || (role === "STOCK_STAFF" && path === "/suppliers");
  if (["/products", "/categories", "/categories-brands", "/brands", "/stock"].includes(path)) return [...stock, "ACCOUNTANT", "VIEWER"].includes(role);
  return true;
}
