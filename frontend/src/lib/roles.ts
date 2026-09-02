export type SystemRole = "BIDDER" | "PROCUREMENT_OFFICER" | "ADMIN";

/**
 * Returns the designated portal landing route for a specific user role.
 */
export function getDashboardRoute(role?: string | null): string {
  switch (role?.toUpperCase()) {
    case "BIDDER":
      return "/bidder";
    case "PROCUREMENT_OFFICER":
      return "/procurement";
    case "ADMIN":
      return "/admin";
    default:
      return "/account";
  }
}

/**
 * Returns a human-friendly role name for display in the UI.
 */
export function getRoleDisplayName(role?: string | null): string {
  switch (role?.toUpperCase()) {
    case "BIDDER":
      return "Bidder / Vendor";
    case "PROCUREMENT_OFFICER":
      return "Procurement Officer";
    case "ADMIN":
      return "System Administrator";
    default:
      return role || "User";
  }
}
