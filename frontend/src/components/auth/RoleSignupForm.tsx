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
  AlertCircle,
  Landmark,
} from "lucide-react";
import { RoleType } from "./RoleLoginForm";

interface RoleSignupConfig {
  name: string;
  badge: string;
  tagline: string;
  subtitle: string;
  primaryColor: string;
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
    if (roleParam === "PROCUREMENT" || roleParam === "PROCUREMENT_OFFICER") {
      return "PROCUREMENT_OFFICER";
    }
    if (roleParam === "ADMIN") {
      return "ADMIN";
    }
    return "BIDDER";
  };

  const [activeRole, setActiveRole] = useState<RoleType>(getInitialRole());
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [organizationType, setOrganizationType] = useState(
    SIGNUP_CONFIGS[getInitialRole()].orgTypeOptions[0]
  );
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
    setOrganizationType(SIGNUP_CONFIGS[role].orgTypeOptions[0]);
    setError(null);
    if (!forcedRole) {
      const paramVal = role === "PROCUREMENT_OFFICER" ? "procurement" : role.toLowerCase();
      router.replace(`/signup?role=${paramVal}`);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!fullName || !email || !password || !organizationName) {
      setError("Please complete all required fields.");
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
      const registeredUser = await signup({
        email: email.trim().toLowerCase(),
        password,
        full_name: fullName.trim(),
        role: activeRole,
        organization_name: organizationName.trim(),
        organization_type: organizationType,
      });

      router.push(getDashboardRoute(registeredUser.role));
    } catch (err: any) {
      setError(
        err?.message || "Failed to register account. Please check your details and try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col justify-center px-4 py-12 sm:px-6 lg:px-8 bg-[#F8FAFC] text-slate-900 font-body">
      <div className="sm:mx-auto sm:w-full sm:max-w-lg text-center">
        {/* Platform Brand */}
        <Link href="/" className="inline-flex items-center gap-2 mb-4 group cursor-pointer">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#0F1E36] text-white shadow-xs">
            <Landmark className="h-4 w-4 text-amber-400" />
          </div>
          <span className="font-heading font-bold text-lg tracking-tight text-[#0F1E36]">
            BidVerify <span className="text-emerald-700 font-extrabold">AI</span>
          </span>
        </Link>

        {/* Role Badge & Title */}
        <div className="flex justify-center mb-2">
          <span className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider bg-slate-100 text-slate-700 border border-slate-200">
            <IconComponent className="h-3.5 w-3.5 text-slate-600" />
            {config.badge}
          </span>
        </div>

        <h2 className="font-heading text-2xl font-bold tracking-tight text-slate-900">
          {config.tagline}
        </h2>
        <p className="mt-1 text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
          {config.subtitle}
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-lg">
        {/* Role Selector Tabs */}
        {showRoleTabs && !forcedRole && (
          <div className="mb-4 grid grid-cols-3 gap-1 rounded-lg bg-white border border-slate-200 p-1 text-xs font-semibold shadow-xs">
            <button
              type="button"
              onClick={() => handleRoleChange("BIDDER")}
              className={`flex items-center justify-center gap-1.5 rounded-md py-2 transition-colors cursor-pointer ${
                activeRole === "BIDDER"
                  ? "bg-[#0F1E36] font-bold text-white shadow-2xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              <Building2 className="h-3.5 w-3.5" />
              <span>Bidder</span>
            </button>

            <button
              type="button"
              onClick={() => handleRoleChange("PROCUREMENT_OFFICER")}
              className={`flex items-center justify-center gap-1.5 rounded-md py-2 transition-colors cursor-pointer ${
                activeRole === "PROCUREMENT_OFFICER"
                  ? "bg-[#0F1E36] font-bold text-white shadow-2xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              <FileCheck2 className="h-3.5 w-3.5" />
              <span>Officer</span>
            </button>

            <button
              type="button"
              onClick={() => handleRoleChange("ADMIN")}
              className={`flex items-center justify-center gap-1.5 rounded-md py-2 transition-colors cursor-pointer ${
                activeRole === "ADMIN"
                  ? "bg-[#0F1E36] font-bold text-white shadow-2xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              <Lock className="h-3.5 w-3.5" />
              <span>Admin</span>
            </button>
          </div>
        )}

        {/* Card Form */}
        <div className="card-formal bg-white rounded-xl p-6 sm:p-8 border border-slate-200">
          {/* Target Role Pill */}
          <div className="mb-4 flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs">
            <span className="font-semibold text-slate-500">Provisioned Role:</span>
            <span className="font-bold px-2 py-0.5 rounded bg-slate-200 text-slate-800 text-[11px]">
              {activeRole}
            </span>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="mb-4 rounded-lg bg-red-50 p-3 border border-red-200 text-xs" role="alert">
              <div className="flex items-start">
                <AlertCircle className="h-4 w-4 text-red-600 mt-0.5 shrink-0" />
                <div className="ml-2">
                  <p className="font-semibold text-red-800">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="fullName" className="block text-xs font-semibold text-slate-700">
                Full Name <span className="text-red-500">*</span>
              </label>
              <div className="mt-1">
                <input
                  id="fullName"
                  name="fullName"
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Adithya Ramanathan"
                  className="input-light-focus block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400"
                />
              </div>
            </div>

            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-slate-700">
                {activeRole === "BIDDER"
                  ? "Business / Work Email"
                  : activeRole === "PROCUREMENT_OFFICER"
                  ? "Official Department Email"
                  : "Administrator Email"}{" "}
                <span className="text-red-500">*</span>
              </label>
              <div className="mt-1">
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
                  className="input-light-focus block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="organizationName" className="block text-xs font-semibold text-slate-700">
                  {config.orgLabel} <span className="text-red-500">*</span>
                </label>
                <div className="mt-1">
                  <input
                    id="organizationName"
                    name="organizationName"
                    type="text"
                    required
                    value={organizationName}
                    onChange={(e) => setOrganizationName(e.target.value)}
                    placeholder={config.orgPlaceholder}
                    className="input-light-focus block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="organizationType" className="block text-xs font-semibold text-slate-700">
                  {config.orgTypeLabel}
                </label>
                <div className="mt-1">
                  <select
                    id="organizationType"
                    name="organizationType"
                    value={organizationType}
                    onChange={(e) => setOrganizationType(e.target.value)}
                    className="input-light-focus block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
                  >
                    {config.orgTypeOptions.map((opt) => (
                      <option key={opt} value={opt} className="bg-white text-slate-900">
                        {opt}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="password" className="block text-xs font-semibold text-slate-700">
                  Password <span className="text-red-500">*</span>
                </label>
                <div className="mt-1">
                  <input
                    id="password"
                    name="password"
                    type="password"
                    autoComplete="new-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Min 8 chars"
                    className="input-light-focus block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="confirmPassword" className="block text-xs font-semibold text-slate-700">
                  Confirm Password <span className="text-red-500">*</span>
                </label>
                <div className="mt-1">
                  <input
                    id="confirmPassword"
                    name="confirmPassword"
                    type="password"
                    autoComplete="new-password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter password"
                    className="input-light-focus block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400"
                  />
                </div>
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isSubmitting}
                className="btn-primary-navy flex w-full justify-center rounded-lg px-4 py-2.5 text-xs font-bold shadow-xs disabled:opacity-50 transition-colors cursor-pointer"
              >
                {isSubmitting ? "Creating Account..." : `Complete ${config.badge}`}
              </button>
            </div>
          </form>

          {/* Already have an account */}
          <div className="mt-5 border-t border-slate-100 pt-3 text-center">
            <p className="text-xs text-slate-500">
              Already have an account?{" "}
              <Link
                href={config.loginUrl}
                className="font-bold text-[#0F1E36] hover:underline transition-colors"
              >
                Sign in to {config.name}
              </Link>
            </p>
          </div>
        </div>

        {/* Back to Home Link */}
        <div className="mt-5 text-center">
          <Link
            href="/"
            className="text-xs text-slate-500 hover:text-slate-900 transition-colors inline-flex items-center gap-1 font-semibold"
          >
            ← Back to GeM Compliance Home
          </Link>
        </div>
      </div>
    </div>
  );
}
