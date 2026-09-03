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
  KeyRound,
  ShieldCheck,
  AlertCircle,
  Sparkles,
  Check,
  Landmark,
} from "lucide-react";

export type RoleType = "BIDDER" | "PROCUREMENT_OFFICER" | "ADMIN";

interface RoleLoginConfig {
  name: string;
  badge: string;
  tagline: string;
  subtitle: string;
  primaryColor: string;
  demoEmail: string;
  demoPass: string;
  signupUrl: string;
  signupText: string;
  icon: React.ElementType;
}

const ROLE_CONFIGS: Record<RoleType, RoleLoginConfig> = {
  BIDDER: {
    name: "Bidder (Vendor)",
    badge: "Bidder Portal",
    tagline: "Vendor Access",
    subtitle: "Submit bid proposals, verify compliance certificates, and participate in open government tenders.",
    primaryColor: "blue",
    demoEmail: "bidder@test.local",
    demoPass: "TestPassword123!",
    signupUrl: "/signup/bidder",
    signupText: "Register Vendor Account",
    icon: Building2,
  },
  PROCUREMENT_OFFICER: {
    name: "Procurement Officer",
    badge: "Procurement Portal",
    tagline: "Procurement Access",
    subtitle: "Publish department tenders, evaluate vendor bids, and perform automated statutory compliance audits.",
    primaryColor: "emerald",
    demoEmail: "procurement@test.local",
    demoPass: "TestPassword123!",
    signupUrl: "/signup/procurement",
    signupText: "Register Official Account",
    icon: FileCheck2,
  },
  ADMIN: {
    name: "Administrator",
    badge: "Admin Oversight",
    tagline: "Platform Admin Access",
    subtitle: "Platform governance, immutable audit trail inspection, user RBAC management, and system monitoring.",
    primaryColor: "purple",
    demoEmail: "admin@test.local",
    demoPass: "TestPassword123!",
    signupUrl: "/signup/admin",
    signupText: "Request Admin Access",
    icon: Lock,
  },
};

interface RoleLoginFormProps {
  forcedRole?: RoleType;
  showRoleTabs?: boolean;
}

export function RoleLoginForm({ forcedRole, showRoleTabs = true }: RoleLoginFormProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, login } = useAuth();

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
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [filledFeedback, setFilledFeedback] = useState(false);

  useEffect(() => {
    if (user) {
      router.push(getDashboardRoute(user.role));
    }
  }, [user, router]);

  useEffect(() => {
    if (forcedRole) {
      setActiveRole(forcedRole);
    } else {
      const roleParam = searchParams.get("role")?.toUpperCase();
      if (roleParam === "PROCUREMENT" || roleParam === "PROCUREMENT_OFFICER") {
        setActiveRole("PROCUREMENT_OFFICER");
      } else if (roleParam === "ADMIN") {
        setActiveRole("ADMIN");
      } else if (roleParam === "BIDDER") {
        setActiveRole("BIDDER");
      }
    }
  }, [forcedRole, searchParams]);

  const config = ROLE_CONFIGS[activeRole];
  const IconComponent = config.icon;

  const handleRoleChange = (role: RoleType) => {
    setActiveRole(role);
    setError(null);
    setEmail("");
    setPassword("");
    setFilledFeedback(false);
    if (!forcedRole) {
      const paramVal = role === "PROCUREMENT_OFFICER" ? "procurement" : role.toLowerCase();
      router.replace(`/login?role=${paramVal}`);
    }
  };

  const handleQuickFill = () => {
    setEmail(config.demoEmail);
    setPassword(config.demoPass);
    setError(null);
    setFilledFeedback(true);
    setTimeout(() => setFilledFeedback(false), 2000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email || !password) {
      setError("Please provide both email and password.");
      return;
    }

    setIsSubmitting(true);
    try {
      const loggedUser = await login({
        email: email.trim().toLowerCase(),
        password,
      });

      router.push(getDashboardRoute(loggedUser.role));
    } catch (err: any) {
      setError(
        err?.message || "Invalid email or password. Please verify your credentials."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col justify-center px-4 py-12 sm:px-6 lg:px-8 bg-[#F8FAFC] text-slate-900 font-body">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
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
        <p className="mt-1 text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
          {config.subtitle}
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
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
          {/* Quick-Fill Demo Account Pill */}
          <div className="mb-4 flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-xs">
            <div className="flex items-center gap-1.5 text-slate-700">
              <KeyRound className="h-3.5 w-3.5 text-slate-500" />
              <span className="text-[11px] text-slate-500 font-medium">Demo:</span>
              <code className="rounded bg-white px-1.5 py-0.5 font-mono text-[11px] text-slate-900 border border-slate-200">
                {config.demoEmail}
              </code>
            </div>
            <button
              type="button"
              onClick={handleQuickFill}
              className="inline-flex items-center gap-1 rounded bg-white border border-slate-300 px-2 py-0.5 font-bold text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer text-[11px]"
            >
              {filledFeedback ? (
                <>
                  <Check className="h-3 w-3 text-emerald-600" />
                  <span className="text-emerald-700">Filled!</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-3 w-3 text-slate-500" />
                  <span>Auto-Fill</span>
                </>
              )}
            </button>
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
              <label htmlFor="email" className="block text-xs font-semibold text-slate-700">
                {activeRole === "BIDDER"
                  ? "Vendor / Work Email"
                  : activeRole === "PROCUREMENT_OFFICER"
                  ? "Official Government Email"
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
                  placeholder={config.demoEmail}
                  className="input-light-focus block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-slate-700">
                Password <span className="text-red-500">*</span>
              </label>
              <div className="mt-1">
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="input-light-focus block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isSubmitting}
                className="btn-primary-navy flex w-full justify-center rounded-lg px-4 py-2.5 text-xs font-bold shadow-xs disabled:opacity-50 transition-colors cursor-pointer"
              >
                {isSubmitting ? "Signing in..." : `Sign in to ${config.badge}`}
              </button>
            </div>
          </form>

          {/* Role-Specific Registration Link */}
          <div className="mt-5 border-t border-slate-100 pt-3 text-center">
            <p className="text-xs text-slate-500">
              Need an account?{" "}
              <Link
                href={config.signupUrl}
                className="font-bold text-[#0F1E36] hover:underline transition-colors"
              >
                {config.signupText}
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
