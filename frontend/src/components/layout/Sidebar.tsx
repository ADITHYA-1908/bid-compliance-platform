"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, ShieldCheck, Landmark } from "lucide-react";
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
    <aside className="hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0 z-30 border-r border-slate-200 bg-white/95 backdrop-blur-xl">
      {/* Brand Header */}
      <div className="flex h-18 shrink-0 items-center gap-3 border-b border-slate-200 px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-900 text-amber-400 shadow-xs border border-slate-700">
          <Landmark className="h-5 w-5" />
        </div>
        <div className="flex flex-col">
          <span className="font-heading text-base font-bold tracking-tight text-slate-900 leading-tight">
            BidVerify <span className="text-emerald-600 font-extrabold">AI</span>
          </span>
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
            GeM Verification
          </span>
        </div>
      </div>

      {/* Role Badge Indicator */}
      <div className="px-6 py-3 border-b border-slate-100 bg-slate-50/70">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider font-heading">
            Portal Scope
          </span>
          <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-bold bg-emerald-50 border border-emerald-200 text-emerald-800 shadow-2xs">
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
                className={`group flex items-center gap-3 rounded-2xl px-3.5 py-2.5 text-xs font-semibold transition-all duration-200 ${
                  isActive
                    ? "nav-item-active-light shadow-2xs"
                    : "text-slate-600 hover:bg-slate-100/80 hover:text-slate-900"
                }`}
              >
                <Icon
                  className={`h-4 w-4 shrink-0 transition-colors ${
                    isActive ? "text-emerald-700" : "text-slate-400 group-hover:text-emerald-600"
                  }`}
                />
                <span className="truncate">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Bottom User & Logout Section */}
      <div className="border-t border-slate-200 p-4">
        <div className="mb-3 rounded-2xl p-3 border border-slate-200 bg-slate-50">
          <p className="text-xs font-bold text-slate-900 truncate">
            {user?.full_name || "User"}
          </p>
          <p className="text-[11px] text-slate-500 truncate">{user?.organization || user?.email}</p>
          <p className="mt-1 text-[10px] font-bold text-emerald-700 font-heading">
            {getRoleDisplayName(user?.role)}
          </p>
        </div>

        <button
          type="button"
          onClick={handleLogout}
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-red-50 hover:text-red-700 hover:border-red-200 transition-all cursor-pointer shadow-2xs"
        >
          <LogOut className="h-3.5 w-3.5" />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
