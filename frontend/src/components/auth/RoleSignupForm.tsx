"use client";

import React, { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { getDashboardRoute } from "@/lib/roles";
import {
  Building2,
  FileCheck2,
  Lock,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
} from "lucide-react";
import { RoleType } from "./RoleLoginForm";

interface RoleSignupConfig {
  name: string;
  badge: string;
  tagline: string;
  subtitle: string;
  primaryColor: string;
  buttonClass: string;
  icon: React.ElementType;
  orgLabel: string;
  orgPlaceholder: string;
  orgTypeLabel: string;
  orgTypeOptions: string[];
  loginUrl: string;
}

const SIGNUP_CONFIGS: Record<RoleType, RoleSignupConfig> = {
  BIDDER: {
    name: "Bidder (Vendor)",
    badge: "Bidder Registration",
    tagline: "Register Vendor Entity",
    subtitle: "Create a vendor account to discover GeM tenders, submit bids, and verify statutory compliance.",
    primaryColor: "blue",
    buttonClass: "bg-blue-900 hover:bg-blue-800 text-white focus-visible:outline-blue-900",
    icon: Building2,
    orgLabel: "Company / Enterprise Name",
    orgPlaceholder: "e.g. ABC Technologies Pvt Ltd",
    orgTypeLabel: "Vendor Entity Structure",
    orgTypeOptions: [
      "Private Limited Company",
      "Public Limited Company",
      "MSME / Small Enterprise",
      "DPIIT Recognized Startup",
      "Partnership / LLP",
      "Sole Proprietorship",
    ],
    loginUrl: "/login/bidder",
  },
  PROCUREMENT_OFFICER: {
    name: "Procurement Officer",
    badge: "Procurement Registration",
    tagline: "Register Procurement Account",
    subtitle: "Create an official buyer account to publish tenders, evaluate bids, and manage contract decisions.",
    primaryColor: "emerald",
    buttonClass: "bg-emerald-900 hover:bg-emerald-800 text-white focus-visible:outline-emerald-900",
    icon: FileCheck2,
    orgLabel: "Ministry / Department / PSU Name",
    orgPlaceholder: "e.g. Ministry of Electronics & IT",
    orgTypeLabel: "Government Entity Type",
    orgTypeOptions: [
      "Central Government Ministry",
      "State Government Department",
      "Public Sector Undertaking (PSU)",
      "Autonomous Government Body",
      "Municipal Corporation / Local Body",
    ],
    loginUrl: "/login/procurement",
  },
  ADMIN: {
    name: "Administrator",
    badge: "Platform Admin Registration",
    tagline: "Register Administrator Account",
    subtitle: "Create a platform oversight account for system governance, role provisioning, and audit oversight.",
    primaryColor: "purple",
    buttonClass: "bg-purple-900 hover:bg-purple-800 text-white focus-visible:outline-purple-900",
    icon: Lock,
    orgLabel: "Platform Oversight Entity",
    orgPlaceholder: "e.g. GeM Platform Oversight Agency",
    orgTypeLabel: "Administration Scope",
    orgTypeOptions: [
      "Platform Oversight Authority",
      "Compliance & Audit Cell",
      "System Operations Management",
    ],
    loginUrl: "/login/admin",
  },
};

interface RoleSignupFormProps {
  forcedRole?: RoleType;
  showRoleTabs?: boolean;
}

export function RoleSignupForm({ forcedRole, showRoleTabs = true }: RoleSignupFormProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, signup } = useAuth();

  const getInitialRole = (): RoleType => {
    if (forcedRole) return forcedRole;
    const roleParam = searchParams.get("role")?.toUpperCase();
    if (roleParam === "PROCUREMENT" || roleParam === "PROCUREMENT_OFFICER" || roleParam === "OFFICER") {
      return "PROCUREMENT_OFFICER";
    }
    if (roleParam === "ADMIN" || roleParam === "ADMINISTRATOR") {
      return "ADMIN";
    }
    return "BIDDER";
  };

  const [activeRole, setActiveRole] = useState<RoleType>(getInitialRole());
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [organizationType, setOrganizationType] = useState(
    SIGNUP_CONFIGS[getInitialRole()].orgTypeOptions[0]
  );
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (user) {
      router.push(getDashboardRoute(user.role));
    }
  }, [user, router]);

  useEffect(() => {
    if (forcedRole) {
      setActiveRole(forcedRole);
      setOrganizationType(SIGNUP_CONFIGS[forcedRole].orgTypeOptions[0]);
    } else {
      const roleParam = searchParams.get("role")?.toUpperCase();
      if (roleParam === "PROCUREMENT" || roleParam === "PROCUREMENT_OFFICER") {
        setActiveRole("PROCUREMENT_OFFICER");
        setOrganizationType(SIGNUP_CONFIGS.PROCUREMENT_OFFICER.orgTypeOptions[0]);
      } else if (roleParam === "ADMIN") {
        setActiveRole("ADMIN");
        setOrganizationType(SIGNUP_CONFIGS.ADMIN.orgTypeOptions[0]);
      } else if (roleParam === "BIDDER") {
        setActiveRole("BIDDER");
        setOrganizationType(SIGNUP_CONFIGS.BIDDER.orgTypeOptions[0]);
      }
    }
  }, [forcedRole, searchParams]);

  const config = SIGNUP_CONFIGS[activeRole];
  const IconComponent = config.icon;

  const handleRoleChange = (role: RoleType) => {
    setActiveRole(role);
    setError(null);
    setOrganizationType(SIGNUP_CONFIGS[role].orgTypeOptions[0]);
    if (!forcedRole) {
      const paramVal = role === "PROCUREMENT_OFFICER" ? "procurement" : role.toLowerCase();
      router.replace(`/signup?role=${paramVal}`);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!fullName.trim() || !email.trim() || !organizationName.trim() || !password) {
      setError("Please fill in all required fields.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match. Please verify.");
      return;
    }

    setIsSubmitting(true);
    try {
      const newUser = await signup({
        full_name: fullName.trim(),
        email: email.trim().toLowerCase(),
        password,
        organization_name: organizationName.trim(),
        organization_type: organizationType,
        role: activeRole,
      });

      router.push(getDashboardRoute(newUser.role));
    } catch (err: any) {
      setError(err?.message || "Failed to create account. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col justify-center px-4 py-12 sm:px-6 lg:px-8 bg-[#0b0f19] text-slate-100 relative overflow-hidden">
      {/* Background ambient glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-purple-900/20 blur-[130px] rounded-full pointer-events-none -z-0" />

      <div className="sm:mx-auto sm:w-full sm:max-w-lg text-center relative z-10">
        {/* Platform Brand */}
        <Link href="/" className="inline-flex items-center gap-2.5 mb-4 group cursor-pointer">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-purple-700 to-indigo-600 shadow-md glow-purple group-hover:scale-105 transition-transform">
            <ShieldCheck className="h-5 w-5 text-white" />
          </div>
          <span className="font-extrabold text-xl tracking-tight text-white">
            BidVerify <span className="text-purple-400">AI</span>
          </span>
        </Link>

        {/* Role Badge & Title */}
        <div className="flex justify-center">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wider border ${
              activeRole === "BIDDER"
                ? "bg-blue-950/70 border-blue-500/30 text-blue-300"
                : activeRole === "PROCUREMENT_OFFICER"
                ? "bg-emerald-950/70 border-emerald-500/30 text-emerald-300"
                : "bg-purple-950/70 border-purple-500/30 text-purple-300"
            }`}
          >
            <IconComponent className="h-3.5 w-3.5" />
            {config.badge}
          </span>
        </div>

        <h2 className="mt-3 text-2xl font-bold tracking-tight text-white sm:text-3xl">
          {config.tagline}
        </h2>
        <p className="mt-2 text-xs sm:text-sm text-slate-400 max-w-md mx-auto leading-relaxed">
          {config.subtitle}
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-lg relative z-10">
        {/* Role Selector Tabs */}
        {showRoleTabs && !forcedRole && (
          <div className="mb-5 grid grid-cols-3 gap-1.5 rounded-xl bg-slate-900/90 border border-slate-800 p-1.5 text-xs font-medium">
            <button
              type="button"
              onClick={() => handleRoleChange("BIDDER")}
              className={`flex items-center justify-center gap-1.5 rounded-lg py-2 transition-all cursor-pointer ${
                activeRole === "BIDDER"
                  ? "bg-blue-600 font-bold text-white shadow-md"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <Building2 className="h-3.5 w-3.5" />
              <span>Bidder</span>
            </button>

            <button
              type="button"
              onClick={() => handleRoleChange("PROCUREMENT_OFFICER")}
              className={`flex items-center justify-center gap-1.5 rounded-lg py-2 transition-all cursor-pointer ${
                activeRole === "PROCUREMENT_OFFICER"
                  ? "bg-emerald-600 font-bold text-white shadow-md"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <FileCheck2 className="h-3.5 w-3.5" />
              <span>Procurement</span>
            </button>

            <button
              type="button"
              onClick={() => handleRoleChange("ADMIN")}
              className={`flex items-center justify-center gap-1.5 rounded-lg py-2 transition-all cursor-pointer ${
                activeRole === "ADMIN"
                  ? "bg-purple-600 font-bold text-white shadow-md"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <Lock className="h-3.5 w-3.5" />
              <span>Admin</span>
            </button>
          </div>
        )}

        {/* Signup Card */}
        <div className="bg-slate-900/90 backdrop-blur-xl px-6 py-8 shadow-2xl ring-1 ring-white/10 sm:rounded-2xl sm:px-10 border border-slate-800">
          {/* Target Role Pill */}
          <div className="mb-5 flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/70 px-3.5 py-2.5 text-xs">
            <span className="font-medium text-slate-400">Provisioned Role:</span>
            <span
              className={`font-bold px-2.5 py-0.5 rounded-md border text-[11px] ${
                activeRole === "BIDDER"
                  ? "bg-blue-950/80 border-blue-500/40 text-blue-300"
                  : activeRole === "PROCUREMENT_OFFICER"
                  ? "bg-emerald-950/80 border-emerald-500/40 text-emerald-300"
                  : "bg-purple-950/80 border-purple-500/40 text-purple-300"
              }`}
            >
              {activeRole}
            </span>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="mb-5 rounded-xl bg-red-950/60 p-3.5 border border-red-800/60 text-xs" role="alert">
              <div className="flex items-start">
                <AlertCircle className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
                <div className="ml-2.5">
                  <p className="font-medium text-red-200 leading-relaxed">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="fullName" className="block text-xs font-semibold text-slate-300">
                Full Name <span className="text-purple-400">*</span>
              </label>
              <div className="mt-1.5">
                <input
                  id="fullName"
                  name="fullName"
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Adithya Ramanathan"
                  className="block w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-slate-300">
                {activeRole === "BIDDER"
                  ? "Business / Work Email"
                  : activeRole === "PROCUREMENT_OFFICER"
                  ? "Official Department Email"
                  : "Administrator Email"}{" "}
                <span className="text-purple-400">*</span>
              </label>
              <div className="mt-1.5">
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={
                    activeRole === "BIDDER"
                      ? "vendor@company.com"
                      : activeRole === "PROCUREMENT_OFFICER"
                      ? "officer@meity.gov.in"
                      : "admin@gem.gov.in"
                  }
                  className="block w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 transition-colors"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="organizationName" className="block text-xs font-semibold text-slate-300">
                  {config.orgLabel} <span className="text-purple-400">*</span>
                </label>
                <div className="mt-1.5">
                  <input
                    id="organizationName"
                    name="organizationName"
                    type="text"
                    required
                    value={organizationName}
                    onChange={(e) => setOrganizationName(e.target.value)}
                    placeholder={config.orgPlaceholder}
                    className="block w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 transition-colors"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="organizationType" className="block text-xs font-semibold text-slate-300">
                  {config.orgTypeLabel}
                </label>
                <div className="mt-1.5">
                  <select
                    id="organizationType"
                    name="organizationType"
                    value={organizationType}
                    onChange={(e) => setOrganizationType(e.target.value)}
                    className="block w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-white focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 transition-colors"
                  >
                    {config.orgTypeOptions.map((opt) => (
                      <option key={opt} value={opt} className="bg-slate-900 text-white">
                        {opt}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="password" className="block text-xs font-semibold text-slate-300">
                  Password <span className="text-purple-400">*</span>
                </label>
                <div className="mt-1.5">
                  <input
                    id="password"
                    name="password"
                    type="password"
                    autoComplete="new-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Min 8 chars"
                    className="block w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 transition-colors"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="confirmPassword" className="block text-xs font-semibold text-slate-300">
                  Confirm Password <span className="text-purple-400">*</span>
                </label>
                <div className="mt-1.5">
                  <input
                    id="confirmPassword"
                    name="confirmPassword"
                    type="password"
                    autoComplete="new-password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter password"
                    className="block w-full rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 transition-colors"
                  />
                </div>
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex w-full justify-center rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-purple-600/25 hover:from-purple-500 hover:to-indigo-500 disabled:opacity-50 transition-all cursor-pointer"
              >
                {isSubmitting ? "Creating Account..." : `Complete ${config.badge}`}
              </button>
            </div>
          </form>

          {/* Already have an account */}
          <div className="mt-6 border-t border-slate-800/80 pt-4 text-center">
            <p className="text-xs text-slate-400">
              Already have an account?{" "}
              <Link
                href={config.loginUrl}
                className="font-semibold text-purple-400 hover:text-purple-300 hover:underline transition-colors"
              >
                Sign in to {config.name}
              </Link>
            </p>
          </div>
        </div>

        {/* Back to Home Link */}
        <div className="mt-6 text-center">
          <Link
            href="/"
            className="text-xs text-slate-400 hover:text-white transition-colors inline-flex items-center gap-1"
          >
            ← Back to GeM Compliance Home
          </Link>
        </div>
      </div>
    </div>
  );
}
