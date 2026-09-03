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
  buttonClass: string;
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
    buttonClass: "btn-emerald-fintech",
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
    buttonClass: "btn-emerald-fintech",
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
    buttonClass: "btn-emerald-fintech",
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
    <div className="flex min-h-screen flex-col justify-center px-4 py-12 sm:px-6 lg:px-8 bg-[#F5F8F7] text-slate-900 selection:bg-emerald-500 selection:text-white font-body relative overflow-x-hidden">
      {/* Background Ambient Blobs */}
      <div className="blob-emerald top-[-100px] left-[20%] opacity-60" />
      <div className="blob-teal top-[300px] right-[15%] opacity-50" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center relative z-10">
        {/* Platform Brand */}
        <Link href="/" className="inline-flex items-center gap-2.5 mb-6 group cursor-pointer">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-900 text-amber-400 shadow-md border border-slate-700 group-hover:scale-105 transition-transform">
            <Landmark className="h-5 w-5" />
          </div>
          <span className="font-heading font-bold text-xl tracking-tight text-slate-900">
            BidVerify <span className="text-emerald-600 font-extrabold">AI</span>
          </span>
        </Link>

        {/* Role Badge & Title */}
        <div className="flex justify-center">
          <span className="inline-flex items-center gap-1.5 rounded-full px-3.5 py-1 text-xs font-bold uppercase tracking-wider bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-xs">
            <IconComponent className="h-3.5 w-3.5 text-emerald-600" />
            {config.badge}
          </span>
        </div>

        <h2 className="mt-4 font-heading text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
          {config.tagline}
        </h2>
        <p className="mt-2 text-xs sm:text-sm text-slate-500 max-w-sm mx-auto leading-relaxed">
          {config.subtitle}
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        {/* Role Selector Tabs */}
        {showRoleTabs && !forcedRole && (
          <div className="mb-5 grid grid-cols-3 gap-1.5 rounded-2xl bg-white border border-slate-200 p-1.5 text-xs font-semibold shadow-xs">
            <button
              type="button"
              onClick={() => handleRoleChange("BIDDER")}
              className={`flex items-center justify-center gap-1.5 rounded-xl py-2.5 transition-all cursor-pointer ${
                activeRole === "BIDDER"
                  ? "btn-emerald-fintech font-bold text-white shadow-xs"
                  : "text-slate-500 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              <Building2 className="h-3.5 w-3.5" />
              <span>Bidder</span>
            </button>

            <button
              type="button"
              onClick={() => handleRoleChange("PROCUREMENT_OFFICER")}
              className={`flex items-center justify-center gap-1.5 rounded-xl py-2.5 transition-all cursor-pointer ${
                activeRole === "PROCUREMENT_OFFICER"
                  ? "btn-emerald-fintech font-bold text-white shadow-xs"
                  : "text-slate-500 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              <FileCheck2 className="h-3.5 w-3.5" />
              <span>Officer</span>
            </button>

            <button
              type="button"
              onClick={() => handleRoleChange("ADMIN")}
              className={`flex items-center justify-center gap-1.5 rounded-xl py-2.5 transition-all cursor-pointer ${
                activeRole === "ADMIN"
                  ? "btn-emerald-fintech font-bold text-white shadow-xs"
                  : "text-slate-500 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              <Lock className="h-3.5 w-3.5" />
              <span>Admin</span>
            </button>
          </div>
        )}

        {/* Floating White Card */}
        <div className="bg-white rounded-3xl px-6 py-8 shadow-xl sm:px-10 border border-slate-200/90">
          {/* Quick-Fill Demo Account Pill */}
          <div className="mb-5 flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50/80 px-3.5 py-2.5 text-xs">
            <div className="flex items-center gap-1.5 text-slate-700">
              <KeyRound className="h-3.5 w-3.5 text-emerald-600" />
              <span className="text-[11px] text-slate-500 font-medium">Demo:</span>
              <code className="rounded bg-white px-2 py-0.5 font-mono-score text-[11px] text-slate-900 border border-slate-200 shadow-2xs">
                {config.demoEmail}
              </code>
            </div>
            <button
              type="button"
              onClick={handleQuickFill}
              className="inline-flex items-center gap-1 rounded-xl bg-emerald-50 border border-emerald-200 px-2.5 py-1 font-bold text-emerald-700 hover:bg-emerald-100 transition-all cursor-pointer shadow-2xs"
            >
              {filledFeedback ? (
                <>
                  <Check className="h-3 w-3 text-emerald-600" />
                  <span className="text-emerald-700 text-[11px]">Filled!</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-3 w-3 text-emerald-600" />
                  <span className="text-[11px]">Auto-Fill</span>
                </>
              )}
            </button>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="mb-5 rounded-2xl bg-red-50 p-3.5 border border-red-200 text-xs" role="alert">
              <div className="flex items-start">
                <AlertCircle className="h-4 w-4 text-red-600 mt-0.5 shrink-0" />
                <div className="ml-2.5">
                  <p className="font-semibold text-red-800 leading-relaxed">{error}</p>
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
                  ? "Official Government / Buyer Email"
                  : "Administrator Email"}{" "}
                <span className="text-emerald-600">*</span>
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
                  placeholder={config.demoEmail}
                  className="input-light-focus block w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 transition-all"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-slate-700">
                Password <span className="text-emerald-600">*</span>
              </label>
              <div className="mt-1.5">
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="input-light-focus block w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 transition-all"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isSubmitting}
                className="btn-emerald-fintech flex w-full justify-center rounded-xl px-4 py-3 text-sm font-bold text-white shadow-md disabled:opacity-50 transition-all cursor-pointer"
              >
                {isSubmitting ? "Signing in..." : `Sign in to ${config.badge}`}
              </button>
            </div>
          </form>

          {/* Role-Specific Registration Link */}
          <div className="mt-6 border-t border-slate-100 pt-4 text-center">
            <p className="text-xs text-slate-500">
              Need an account?{" "}
              <Link
                href={config.signupUrl}
                className="font-bold text-emerald-600 hover:text-emerald-700 hover:underline transition-colors"
              >
                {config.signupText}
              </Link>
            </p>
          </div>
        </div>

        {/* Back to Home Link */}
        <div className="mt-6 text-center">
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
