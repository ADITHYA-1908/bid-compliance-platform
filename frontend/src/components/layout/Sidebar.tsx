"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, Landmark } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { NAVIGATION_BY_ROLE, NavItem } from "@/config/navigation";
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

  // Group items by category
  const categories: string[] = [];
  const itemsByCategory: Record<string, NavItem[]> = {};

  navItems.forEach((item) => {
    const cat = item.category || "GENERAL";
    if (!categories.includes(cat)) {
      categories.push(cat);
      itemsByCategory[cat] = [];
    }
    itemsByCategory[cat].push(item);
  });

  return (
    <aside className="hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0 z-30 border-r border-slate-200 bg-white">
      {/* Brand Header */}
      <div className="flex h-14 shrink-0 items-center gap-3 border-b border-slate-200 px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#0F1E36] text-white shadow-2xs">
          <Landmark className="h-4 w-4 text-amber-400" />
        </div>
        <div className="flex flex-col">
          <span className="font-heading text-sm font-bold tracking-tight text-[#0F1E36] leading-tight">
            BidVerify <span className="text-emerald-700 font-extrabold">AI</span>
          </span>
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
            Government Compliance
          </span>
        </div>
      </div>

      {/* Role Badge Indicator */}
      <div className="px-5 py-2.5 border-b border-slate-100 bg-slate-50">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
            Portal Scope
          </span>
          <span className="inline-flex items-center rounded px-2 py-0.5 text-[10px] font-bold bg-slate-200/80 text-slate-800">
            {roleConfig.portalName.split(" ")[0]}
          </span>
        </div>
      </div>

      {/* Navigation Items grouped by category */}
      <div className="flex flex-1 flex-col overflow-y-auto px-3 py-3 space-y-4">
        {categories.map((cat) => (
          <div key={cat} className="space-y-1">
            <div className="px-2 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              {cat}
            </div>
            <nav className="space-y-0.5">
              {itemsByCategory[cat].map((item) => {
                const Icon = item.icon;
                const isActive =
                  pathname === item.href ||
                  (item.href !== `/${userRole.toLowerCase()}` &&
                    pathname.startsWith(item.href));

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-semibold transition-colors ${
                      isActive
                        ? "nav-item-active-light bg-slate-100 text-[#0F1E36]"
                        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                    }`}
                  >
                    <Icon
                      className={`h-4 w-4 shrink-0 transition-colors ${
                        isActive ? "text-[#0F1E36]" : "text-slate-400 group-hover:text-slate-700"
                      }`}
                    />
                    <span className="truncate">{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>
        ))}
      </div>

      {/* Bottom Sign Out */}
      <div className="border-t border-slate-200 p-3 bg-slate-50/50">
        <button
          type="button"
          onClick={handleLogout}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 hover:text-slate-900 transition-colors cursor-pointer shadow-2xs"
        >
          <LogOut className="h-3.5 w-3.5 text-slate-500" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
