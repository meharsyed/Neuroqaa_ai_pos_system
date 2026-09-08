import type { User, UserRole } from "@/types/auth";

/**
 * What each role may do.
 *
 * The server enforces all of this — these helpers exist so the interface does
 * not offer a cashier buttons and pages that will only ever answer 403. Never
 * treat them as the security boundary; they are the manners.
 */

export const ROLE_LABEL: Record<UserRole, string> = {
  owner: "Owner",
  manager: "Manager",
  cashier: "Cashier",
  stock_clerk: "Stock Clerk",
};

const role = (user: User | null | undefined): UserRole | null => user?.role ?? null;

/** Owner and manager: money decisions, prices, reports. */
export const isManagement = (user: User | null | undefined) =>
  role(user) === "owner" || role(user) === "manager";

/** Owner alone: staff accounts, the activity log, shop settings. */
export const isOwner = (user: User | null | undefined) => role(user) === "owner";

export const can = {
  /** Change prices, add stock, archive a product. */
  editCatalogue: isManagement,
  /** See cost price and margin. The server strips these fields anyway. */
  seeCostPrices: isManagement,
  /** Void a completed sale. */
  voidSale: isManagement,
  /** Reports, the audit P&L, inventory valuation. */
  viewReports: isManagement,
  /** Set a customer's credit limit. */
  setCreditLimit: isManagement,
  /** The security trail, staff accounts and shop settings. */
  viewActivityLog: isOwner,
  manageUsers: isOwner,
  editSettings: isManagement,
};

/**
 * Which routes a role may open. Anything not listed is open to everyone
 * signed in — the till, bills, customers and the khata are everyone's job.
 */
export const ROUTE_ACCESS: Record<string, (u: User | null | undefined) => boolean> = {
  "/audit": can.viewReports,
  "/activity": can.viewActivityLog,
  "/settings": can.editSettings,
  "/users": can.manageUsers,
};

export function mayOpen(path: string, user: User | null | undefined): boolean {
  const guard = ROUTE_ACCESS[path];
  return guard ? guard(user) : true;
}
