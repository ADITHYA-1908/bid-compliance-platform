import {
  LayoutDashboard,
  FileText,
  Send,
  Files,
  MessageSquareQuote,
  CheckSquare,
  ShieldCheck,
  BarChart3,
  Users,
  Building2,
  History,
  TrendingUp,
  Award,
  LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  description?: string;
  category?: string;
}

export interface RoleNavigationConfig {
  portalName: string;
  badgeColor: string;
  items: NavItem[];
}

export const NAVIGATION_BY_ROLE: Record<string, RoleNavigationConfig> = {
  BIDDER: {
    portalName: "Bidder Portal",
    badgeColor: "bg-blue-50 text-blue-800 border-blue-200",
    items: [
      {
        label: "Dashboard",
        href: "/bidder",
        icon: LayoutDashboard,
        category: "OVERVIEW",
      },
      {
        label: "Available Tenders",
        href: "/bidder/tenders",
        icon: FileText,
        description: "Discover active GeM procurement opportunities and tenders",
        category: "OPPORTUNITIES",
      },
      {
        label: "My Bids",
        href: "/bidder/bids",
        icon: Send,
        description: "Track and manage submitted bid packages",
        category: "SUBMISSIONS",
      },
      {
        label: "Documents Vault",
        href: "/bidder/documents",
        icon: Files,
        description: "Compliance documents repository and verified credentials",
        category: "SUBMISSIONS",
      },
      {
        label: "Clarifications",
        href: "/bidder/clarifications",
        icon: MessageSquareQuote,
        description: "Buyer clarification queries and response submissions",
        category: "COMPLIANCE",
      },
      {
        label: "Certificates",
        href: "/bidder/certificates",
        icon: Award,
        description: "Track certificate expiration, renewal countdown, and validity",
        category: "COMPLIANCE",
      },
      {
        label: "Organization Profile",
        href: "/bidder/organization",
        icon: Building2,
        description: "Organization details, GST, PAN, and Udyam credentials",
        category: "ENTITY",
      },
    ],
  },
  PROCUREMENT_OFFICER: {
    portalName: "Procurement Portal",
    badgeColor: "bg-emerald-50 text-emerald-800 border-emerald-200",
    items: [
      {
        label: "Dashboard",
        href: "/procurement",
        icon: LayoutDashboard,
        category: "OVERVIEW",
      },
      {
        label: "Tenders",
        href: "/procurement/tenders",
        icon: FileText,
        description: "Publish and manage departmental procurement tenders",
        category: "PROCUREMENT",
      },
      {
        label: "Bids & Evaluations",
        href: "/procurement/evaluations",
        icon: CheckSquare,
        description: "Technical, commercial, and financial bid comparisons",
        category: "PROCUREMENT",
      },
      {
        label: "Review Queue",
        href: "/procurement/reviews",
        icon: ShieldCheck,
        description: "Review and resolve flagged evidence, ambiguities, and critical findings",
        category: "PROCUREMENT",
      },
      {
        label: "Clarifications",
        href: "/procurement/clarifications",
        icon: MessageSquareQuote,
        description: "Issue and review formal clarification requests to bidders",
        category: "PROCUREMENT",
      },
      {
        label: "Analytics",
        href: "/procurement/analytics",
        icon: TrendingUp,
        description: "Procurement intelligence, compliance distribution, and time savings",
        category: "INSIGHTS",
      },
      {
        label: "Validation",
        href: "/procurement/validation",
        icon: BarChart3,
        description: "Empirical performance benchmark, OCR & extraction metrics",
        category: "INSIGHTS",
      },
      {
        label: "Audit Trail",
        href: "/procurement/audit",
        icon: History,
        description: "Immutable chronological event log and decision version history",
        category: "SYSTEM",
      },
    ],
  },
  ADMIN: {
    portalName: "Admin Oversight Portal",
    badgeColor: "bg-purple-50 text-purple-800 border-purple-200",
    items: [
      {
        label: "Dashboard",
        href: "/admin",
        icon: LayoutDashboard,
        category: "OVERVIEW",
      },
      {
        label: "Organizations",
        href: "/admin/organizations",
        icon: Building2,
        description: "Registered ministries, CPSEs, and vendor organizations",
        category: "GOVERNANCE",
      },
      {
        label: "Users",
        href: "/admin/users",
        icon: Users,
        description: "Platform user accounts, status, and permission oversight",
        category: "GOVERNANCE",
      },
      {
        label: "Validation Benchmark",
        href: "/admin/validation",
        icon: BarChart3,
        description: "Empirical benchmark suite, accuracy metrics, and speedup",
        category: "BENCHMARK",
      },
      {
        label: "Platform Audit Log",
        href: "/procurement/audit",
        icon: History,
        description: "Chronological immutable platform audit events",
        category: "SYSTEM",
      },
    ],
  },
};
