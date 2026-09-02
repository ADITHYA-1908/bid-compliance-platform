"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, ShieldCheck } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { NAVIGATION_BY_ROLE } from "@/config/navigation";
import { getRoleDisplayName } from "@/lib/roles";

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  const userRole = user?.role?.toUpperCase() || "BIDDER";
  const roleConfig = NAVIGATION_BY_ROLE[userRole] || NAVIGATION_BY_ROLE.BIDDER;
  const navItems = roleConfig.items;

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <aside className="hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0 z-30 border-r border-cyan-500/15 bg-[#060a17]/95 backdrop-blur-xl">
      {/* Brand Header */}
      <div className="flex h-16 shrink-0 items-center gap-3 border-b border-cyan-500/15 px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-600 to-emerald-500 text-white shadow-md glow-cyan">
          <ShieldCheck className="h-5 w-5" />
        </div>
        <div className="flex flex-col">
          <span className="text-base font-extrabold tracking-tight text-white leading-tight">
            BidVerify <span className="gradient-text-cyan-emerald font-extrabold">AI</span>
          </span>
          <span className="text-[10px] font-bold text-cyan-300/80 uppercase tracking-wider">
            GeM Verification
          </span>
        </div>
      </div>

      {/* Role Badge Indicator */}
      <div className="px-6 py-3 border-b border-cyan-500/10 bg-slate-950/60">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            Portal Scope
          </span>
          <span className="inline-flex items-center rounded-lg px-2.5 py-0.5 text-[10px] font-bold bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 shadow-sm">
            {roleConfig.portalName.split(" ")[0]}
          </span>
        </div>
      </div>

      {/* Navigation Items */}
      <div className="flex flex-1 flex-col overflow-y-auto px-4 py-4 space-y-1">
        <nav className="flex-1 space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              pathname === item.href ||
              (item.href !== `/${userRole.toLowerCase()}` &&
                pathname.startsWith(item.href));

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-bold transition-all duration-200 ${
                  isActive
                    ? "nav-item-active text-white shadow-lg shadow-cyan-500/10"
                    : "text-slate-300 hover:bg-slate-900/80 hover:text-white"
                }`}
              >
                <Icon
                  className={`h-4 w-4 shrink-0 transition-colors ${
                    isActive ? "text-cyan-300" : "text-slate-400 group-hover:text-cyan-300"
                  }`}
                />
                <span className="truncate">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Bottom User & Logout Section */}
      <div className="border-t border-cyan-500/15 p-4">
        <div className="mb-3 rounded-xl glass-card p-3 border border-cyan-500/20 bg-slate-950/70">
          <p className="text-xs font-bold text-white truncate">
            {user?.full_name || "User"}
          </p>
          <p className="text-[11px] text-slate-300 truncate">{user?.organization || user?.email}</p>
          <p className="mt-1 text-[10px] font-extrabold text-cyan-400">
            {getRoleDisplayName(user?.role)}
          </p>
        </div>

        <button
          type="button"
          onClick={handleLogout}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-xs font-semibold text-slate-300 hover:bg-red-950/50 hover:text-red-300 hover:border-red-800/60 transition-all cursor-pointer"
        >
          <LogOut className="h-3.5 w-3.5" />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
