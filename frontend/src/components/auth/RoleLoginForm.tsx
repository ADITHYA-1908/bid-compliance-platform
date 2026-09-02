"use client";

import React, { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { getDashboardRoute } from "@/lib/roles";
import {
  Building2,
  FileCheck2,
  ShieldCheck,
  Lock,
  ArrowRight,
  Sparkles,
  AlertCircle,
  KeyRound,
  Check,
} from "lucide-react";

export type RoleType = "BIDDER" | "PROCUREMENT_OFFICER" | "ADMIN";

interface RoleConfig {
  name: string;
  badge: string;
  tagline: string;
  subtitle: string;
  primaryColor: string;
  bgLight: string;
  borderActive: string;
  buttonClass: string;
  icon: React.ElementType;
  demoEmail: string;
  demoPass: string;
  signupUrl: string;
  signupText: string;
}

const ROLE_CONFIGS: Record<RoleType, RoleConfig> = {
  BIDDER: {
    name: "Bidder (Vendor)",
    badge: "Bidder Portal",
    tagline: "Vendor & Bidder Login",
    subtitle: "Submit tender bids, upload compliance proof, and track AI verification status.",
    primaryColor: "blue",
    bgLight: "bg-blue-50/50",
    borderActive: "border-blue-600 ring-2 ring-blue-600/20",
    buttonClass: "bg-blue-900 hover:bg-blue-800 text-white focus-visible:outline-blue-900",
    icon: Building2,
    demoEmail: "bidder@test.local",
    demoPass: "TestPassword123!",
    signupUrl: "/signup/bidder",
    signupText: "Register as Bidder",
  },
  PROCUREMENT_OFFICER: {
    name: "Procurement Officer",
    badge: "Procurement Portal",
    tagline: "Procurement Officer Login",
    subtitle: "Publish tenders, evaluate vendor bids, review AI scoring, and manage contract awards.",
    primaryColor: "emerald",
    bgLight: "bg-emerald-50/50",
    borderActive: "border-emerald-600 ring-2 ring-emerald-600/20",
    buttonClass: "bg-emerald-900 hover:bg-emerald-800 text-white focus-visible:outline-emerald-900",
    icon: FileCheck2,
    demoEmail: "procurement@test.local",
    demoPass: "TestPassword123!",
    signupUrl: "/signup/procurement",
    signupText: "Register as Procurement Officer",
  },
  ADMIN: {
    name: "Administrator",
    badge: "Platform Admin",
    tagline: "System Administrator Login",
    subtitle: "System governance, user roles, security audits, and organizational oversight.",
    primaryColor: "purple",
    bgLight: "bg-purple-50/50",
    borderActive: "border-purple-600 ring-2 ring-purple-600/20",
    buttonClass: "bg-purple-900 hover:bg-purple-800 text-white focus-visible:outline-purple-900",
    icon: Lock,
    demoEmail: "admin@test.local",
    demoPass: "TestPassword123!",
    signupUrl: "/signup/admin",
    signupText: "Register as Administrator",
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
      setError("Please enter both email and password.");
      return;
    }

    setIsSubmitting(true);
    try {
      const authenticatedUser = await login({
        email,
        password,
        expected_role: activeRole,
      });
      router.push(getDashboardRoute(authenticatedUser.role));
    } catch (err: any) {
      setError(err?.message || "Invalid credentials. Please verify and try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col justify-center px-4 py-12 sm:px-6 lg:px-8 bg-[#040711] text-slate-100 relative overflow-hidden selection:bg-cyan-500 selection:text-white">
      {/* 3D Verification Particle Canvas */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none z-0 opacity-70"
      />

      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center relative z-10">
        {/* Platform Brand */}
        <Link href="/" className="inline-flex items-center gap-2.5 mb-4 group cursor-pointer">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-600 to-emerald-500 shadow-lg glow-cyan group-hover:scale-105 transition-transform">
            <ShieldCheck className="h-6 w-6 text-white" />
          </div>
          <span className="font-extrabold text-2xl tracking-tight text-white">
            BidVerify <span className="gradient-text-cyan-emerald font-extrabold">AI</span>
          </span>
        </Link>

        {/* Role Badge & Title */}
        <div className="flex justify-center">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1 text-xs font-bold uppercase tracking-wider border shadow-md ${
              activeRole === "BIDDER"
                ? "bg-cyan-950/90 border-cyan-500/40 text-cyan-300"
                : activeRole === "PROCUREMENT_OFFICER"
                ? "bg-emerald-950/90 border-emerald-500/40 text-emerald-300"
                : "bg-cyan-950/90 border-cyan-400/40 text-cyan-300"
            }`}
          >
            <IconComponent className="h-3.5 w-3.5" />
            {config.badge}
          </span>
        </div>

        <h2 className="mt-4 text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
          {config.tagline}
        </h2>
        <p className="mt-2 text-xs sm:text-sm text-slate-300 max-w-sm mx-auto leading-relaxed">
          {config.subtitle}
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        {/* Role Selector Tabs */}
        {showRoleTabs && !forcedRole && (
          <div className="mb-5 grid grid-cols-3 gap-1.5 rounded-xl bg-slate-950/90 border border-cyan-500/20 p-1.5 text-xs font-semibold backdrop-blur-md shadow-xl">
            <button
              type="button"
              onClick={() => handleRoleChange("BIDDER")}
              className={`flex items-center justify-center gap-1.5 rounded-lg py-2.5 transition-all cursor-pointer ${
                activeRole === "BIDDER"
                  ? "bg-cyan-600 font-bold text-white shadow-md glow-cyan"
                  : "text-slate-400 hover:text-white hover:bg-slate-900/60"
              }`}
            >
              <Building2 className="h-3.5 w-3.5" />
              <span>Bidder</span>
            </button>

            <button
              type="button"
              onClick={() => handleRoleChange("PROCUREMENT_OFFICER")}
              className={`flex items-center justify-center gap-1.5 rounded-lg py-2.5 transition-all cursor-pointer ${
                activeRole === "PROCUREMENT_OFFICER"
                  ? "bg-emerald-600 font-bold text-white shadow-md glow-emerald"
                  : "text-slate-400 hover:text-white hover:bg-slate-900/60"
              }`}
            >
              <FileCheck2 className="h-3.5 w-3.5" />
              <span>Officer</span>
            </button>

            <button
              type="button"
              onClick={() => handleRoleChange("ADMIN")}
              className={`flex items-center justify-center gap-1.5 rounded-lg py-2.5 transition-all cursor-pointer ${
                activeRole === "ADMIN"
                  ? "btn-cyan-emerald font-bold text-slate-950 shadow-md"
                  : "text-slate-400 hover:text-white hover:bg-slate-900/60"
              }`}
            >
              <Lock className="h-3.5 w-3.5" />
              <span>Admin</span>
            </button>
          </div>
        )}

        {/* Login Card */}
        <div className="glass-card bg-[#0b1329]/85 backdrop-blur-2xl px-6 py-8 shadow-2xl rounded-2xl sm:px-10 border border-cyan-500/20">
          {/* Quick-Fill Demo Account Pill */}
          <div className="mb-5 flex items-center justify-between rounded-xl border border-cyan-500/20 bg-slate-950/80 px-3.5 py-2.5 text-xs">
            <div className="flex items-center gap-1.5 text-slate-300">
              <KeyRound className="h-3.5 w-3.5 text-cyan-400" />
              <span className="text-[11px] text-slate-400 font-medium">Demo:</span>
              <code className="rounded bg-slate-900/90 px-1.5 py-0.5 font-mono text-[11px] text-cyan-300 border border-cyan-500/20">
                {config.demoEmail}
              </code>
            </div>
            <button
              type="button"
              onClick={handleQuickFill}
              className="inline-flex items-center gap-1 rounded-lg bg-cyan-950/90 border border-cyan-500/40 px-2.5 py-1 font-bold text-cyan-300 hover:bg-cyan-900/90 transition-all cursor-pointer shadow-sm"
            >
              {filledFeedback ? (
                <>
                  <Check className="h-3 w-3 text-emerald-400" />
                  <span className="text-emerald-400 text-[11px]">Filled!</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-3 w-3 text-cyan-400" />
                  <span className="text-[11px]">Auto-Fill</span>
                </>
              )}
            </button>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="mb-5 rounded-xl bg-red-950/70 p-3.5 border border-red-800/70 text-xs" role="alert">
              <div className="flex items-start">
                <AlertCircle className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
                <div className="ml-2.5">
                  <p className="font-semibold text-red-200 leading-relaxed">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-slate-200">
                {activeRole === "BIDDER"
                  ? "Vendor / Work Email"
                  : activeRole === "PROCUREMENT_OFFICER"
                  ? "Official Government / Buyer Email"
                  : "Administrator Email"}{" "}
                <span className="text-cyan-400">*</span>
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
                  className="input-glow block w-full rounded-xl border border-slate-800 bg-[#040711] px-3.5 py-2.5 text-sm text-white placeholder:text-slate-500 transition-all"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-slate-200">
                Password <span className="text-cyan-400">*</span>
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
                  className="input-glow block w-full rounded-xl border border-slate-800 bg-[#040711] px-3.5 py-2.5 text-sm text-white placeholder:text-slate-500 transition-all"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isSubmitting}
                className="btn-cyan-emerald flex w-full justify-center rounded-xl px-4 py-3 text-sm font-bold text-slate-950 shadow-xl disabled:opacity-50 transition-all cursor-pointer"
              >
                {isSubmitting ? "Signing in..." : `Sign in to ${config.badge}`}
              </button>
            </div>
          </form>

          {/* Role-Specific Registration Link */}
          <div className="mt-6 border-t border-slate-800/80 pt-4 text-center">
            <p className="text-xs text-slate-400">
              Need an account?{" "}
              <Link
                href={config.signupUrl}
                className="font-bold text-cyan-400 hover:text-cyan-300 hover:underline transition-colors"
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
            className="text-xs text-slate-400 hover:text-white transition-colors inline-flex items-center gap-1 font-medium"
          >
            ← Back to GeM Compliance Home
          </Link>
        </div>
      </div>
    </div>
  );
}
