import React from "react";
import {
  LayoutDashboard,
  User,
  Building2,
  FileText,
  Send,
  Files,
  BadgeCheck,
  MessageSquareQuote,
  Bell,
  CheckSquare,
  ShieldCheck,
  BarChart3,
  Users,
  Shield,
  Settings,
  Network,
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
  phase?: string;
}

export interface RoleNavigationConfig {
  portalName: string;
  badgeColor: string;
  items: NavItem[];
}

export const NAVIGATION_BY_ROLE: Record<string, RoleNavigationConfig> = {
  BIDDER: {
    portalName: "Bidder Portal",
    badgeColor: "bg-blue-100 text-blue-800 border-blue-200",
    items: [
      {
        label: "Dashboard",
        href: "/bidder",
        icon: LayoutDashboard,
      },
      {
        label: "My Profile",
        href: "/bidder/profile",
        icon: User,
        description: "Manage personal profile and bidder credentials",
        phase: "Part 2",
      },
      {
        label: "My Organization",
        href: "/bidder/organization",
        icon: Building2,
        description: "Organization details, GST, PAN, and Udyam credentials",
        phase: "Part 2",
      },
      {
        label: "Tenders",
        href: "/bidder/tenders",
        icon: FileText,
        description: "Browse GeM procurement opportunities and tenders",
        phase: "Part 3",
      },
      {
        label: "My Bids",
        href: "/bidder/bids",
        icon: Send,
        description: "Track and manage submitted bid packages",
        phase: "Part 3",
      },
      {
        label: "Documents",
        href: "/bidder/documents",
        icon: Files,
        description: "Bidder compliance documents vault and technical submissions",
        phase: "Part 4",
      },
      {
        label: "Verification Status",
        href: "/bidder/verification",
        icon: BadgeCheck,
        description: "AI-assisted compliance scoring and verification results",
        phase: "Part 5",
      },
      {
        label: "Clarifications",
        href: "/bidder/clarifications",
        icon: MessageSquareQuote,
        description: "Buyer clarification requests and bidder responses",
        phase: "Part 6",
      },
      {
        label: "Notifications",
        href: "/bidder/notifications",
        icon: Bell,
        description: "Tender updates, deadline reminders, and audit notices",
        phase: "Part 7",
      },
      {
        label: "Certificates & Validity",
        href: "/bidder/certificates",
        icon: Award,
        description: "Track certificate expiration, renewal countdown, and validity",
        phase: "Part 14",
      },
    ],
  },
  PROCUREMENT_OFFICER: {
    portalName: "Procurement Officer Portal",
    badgeColor: "bg-purple-100 text-purple-800 border-purple-200",
    items: [
      {
        label: "Dashboard",
        href: "/procurement",
        icon: LayoutDashboard,
      },
      {
        label: "Tenders",
        href: "/procurement/tenders",
        icon: FileText,
        description: "Publish and manage departmental procurement tenders",
        phase: "Part 2",
      },
      {
        label: "Bidders",
        href: "/procurement/bidders",
        icon: Building2,
        description: "Participating vendor directory and statutory eligibility",
        phase: "Part 3",
      },
      {
        label: "Bid Evaluations",
        href: "/procurement/evaluations",
        icon: CheckSquare,
        description: "Technical, commercial, and financial bid comparisons",
        phase: "Part 4",
      },
      {
        label: "Human Review Queue",
        href: "/procurement/reviews",
        icon: ShieldCheck,
        description: "Review and resolve flagged evidence, ambiguities, and critical findings",
        phase: "Part 8C",
      },
      {
        label: "Compliance Review",
        href: "/procurement/compliance",
        icon: ShieldCheck,
        description: "Automated clause-by-clause statutory compliance audit",
        phase: "Part 5",
      },
      {
        label: "Verification Center",
        href: "/procurement/verifications",
        icon: BadgeCheck,
        description: "Integrity checks, blacklisting queries, and anomaly alerts",
        phase: "Part 5",
      },
      {
        label: "Clarifications",
        href: "/procurement/clarifications",
        icon: MessageSquareQuote,
        description: "Issue and review formal clarification requests to bidders",
        phase: "Part 6",
      },
      {
        label: "Reports",
        href: "/procurement/reports",
        icon: BarChart3,
        description: "Evaluation summaries, audit dossiers, and GeM export sheets",
        phase: "Part 8E",
      },
      {
        label: "Audit Trail",
        href: "/procurement/audit",
        icon: History,
        description: "Immutable chronological event log and decision version history",
        phase: "Part 8E",
      },
      {
        label: "Analytics & Impact",
        href: "/procurement/analytics",
        icon: TrendingUp,
        description: "Procurement intelligence, compliance distribution, and time savings",
        phase: "Part 13",
      },
      {
        label: "Certificates & Validity",
        href: "/procurement/certificates",
        icon: Award,
        description: "Monitor statutory certificate expiration and validity countdown",
        phase: "Part 14",
      },
      {
        label: "Validation & Benchmark",
        href: "/procurement/validation",
        icon: BarChart3,
        description: "Empirical performance benchmark, OCR & extraction metrics",
        phase: "Validation",
      },
    ],
  },
  ADMIN: {
    portalName: "Admin Portal",
    badgeColor: "bg-rose-100 text-rose-800 border-rose-200",
    items: [
      {
        label: "Dashboard",
        href: "/admin",
        icon: LayoutDashboard,
      },
      {
        label: "Users",
        href: "/admin/users",
        icon: Users,
        description: "Platform user accounts, status, and permission oversight",
        phase: "Part 2",
      },
      {
        label: "Organizations",
        href: "/admin/organizations",
        icon: Building2,
        description: "Registered ministries, CPSEs, and vendor organizations",
        phase: "Part 2",
      },
      {
        label: "System Roles",
        href: "/admin/roles",
        icon: Shield,
        description: "RBAC security policies and access matrix definitions",
        phase: "Part 2",
      },
      {
        label: "Certificates & Validity",
        href: "/admin/certificates",
        icon: Award,
        description: "Platform-wide certificate validity surveillance and batch scan",
        phase: "Part 14",
      },
      {
        label: "Analytics & Impact",
        href: "/admin/analytics",
        icon: TrendingUp,
        description: "Platform-wide analytics, risk radar, and impact metrics",
        phase: "Part 13",
      },
      {
        label: "Validation & Benchmark",
        href: "/admin/validation",
        icon: BarChart3,
        description: "Empirical benchmark suite, accuracy metrics, and speedup",
        phase: "Validation",
      },
      {
        label: "System Settings",
        href: "/admin/settings",
        icon: Settings,
        description: "Platform parameters, audit policies, and security limits",
        phase: "Part 6",
      },
      {
        label: "Integration Status",
        href: "/admin/integrations",
        icon: Network,
        description: "GeM API bridge, Supabase PostgreSQL, and OCR services",
        phase: "Part 7",
      },
    ],
  },
};
