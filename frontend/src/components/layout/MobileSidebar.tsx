"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { X, LogOut, Landmark } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { NAVIGATION_BY_ROLE } from "@/config/navigation";
import { getRoleDisplayName } from "@/lib/roles";

interface MobileSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function MobileSidebar({ isOpen, onClose }: MobileSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  if (!isOpen) return null;

  const userRole = user?.role?.toUpperCase() || "BIDDER";
  const roleConfig = NAVIGATION_BY_ROLE[userRole] || NAVIGATION_BY_ROLE.BIDDER;
  const navItems = roleConfig.items;

  const handleLogout = () => {
    onClose();
    logout();
    router.push("/login");
  };

  return (
    <div className="relative z-50 lg:hidden">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      <div className="fixed inset-0 flex">
        <div className="relative mr-16 flex w-full max-w-xs flex-1 flex-col bg-white/95 backdrop-blur-2xl border-r border-slate-200">
          {/* Header & Close button */}
          <div className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 px-6">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-slate-900 text-amber-400 border border-slate-700 shadow-2xs">
                <Landmark className="h-4 w-4" />
              </div>
              <span className="font-heading text-base font-bold tracking-tight text-slate-900">
                BidVerify <span className="text-emerald-600 font-extrabold">AI</span>
              </span>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 cursor-pointer transition-colors"
              aria-label="Close navigation menu"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Role badge */}
          <div className="px-6 py-2.5 border-b border-slate-100 bg-slate-50/70">
            <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-bold bg-emerald-50 border border-emerald-200 text-emerald-800 shadow-2xs">
              {roleConfig.portalName}
            </span>
          </div>

          {/* Navigation Items */}
          <div className="flex-1 overflow-y-auto px-4 py-4">
            <nav className="space-y-1.5">
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
                    onClick={onClose}
                    className={`flex items-center gap-3 rounded-2xl px-3.5 py-2.5 text-xs font-semibold transition-all ${
                      isActive
                        ? "nav-item-active-light shadow-2xs"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    }`}
                  >
                    <Icon className={`h-4 w-4 shrink-0 ${isActive ? "text-emerald-700" : "text-slate-400"}`} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Bottom user card & logout */}
          <div className="border-t border-slate-200 p-4">
            <div className="mb-3 rounded-2xl p-3 border border-slate-200 bg-slate-50">
              <p className="text-xs font-bold text-slate-900 truncate">
                {user?.full_name || "User"}
              </p>
              <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
              <p className="text-[10px] text-emerald-700 font-bold mt-0.5 font-heading">
                {getRoleDisplayName(user?.role)}
              </p>
            </div>

            <button
              type="button"
              onClick={handleLogout}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-red-50 hover:text-red-700 hover:border-red-200 transition-colors cursor-pointer shadow-2xs"
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
