"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { X, LogOut, ShieldCheck } from "lucide-react";
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

  // Close when pathname changes
  useEffect(() => {
    onClose();
  }, [pathname, onClose]);

  // Prevent scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const userRole = user?.role?.toUpperCase() || "BIDDER";
  const roleConfig = NAVIGATION_BY_ROLE[userRole] || NAVIGATION_BY_ROLE.BIDDER;
  const navItems = roleConfig.items;

  const handleLogout = () => {
    logout();
    onClose();
    router.push("/login");
  };

  return (
    <div className="relative z-50 lg:hidden" role="dialog" aria-modal="true">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      <div className="fixed inset-0 flex">
        <div className="relative mr-16 flex w-full max-w-xs flex-1 flex-col bg-slate-950/95 backdrop-blur-xl border-r border-slate-800">
          {/* Header & Close button */}
          <div className="flex h-16 shrink-0 items-center justify-between border-b border-slate-800 px-6">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-tr from-purple-700 to-indigo-600 text-white shadow-md">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <span className="text-base font-extrabold tracking-tight text-white">
                BidVerify <span className="text-purple-400">AI</span>
              </span>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="rounded-md p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white cursor-pointer transition-colors"
              aria-label="Close navigation menu"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Role badge */}
          <div className="px-6 py-2.5 border-b border-slate-800/60 bg-slate-900/40">
            <span className="inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-bold bg-purple-950/70 border border-purple-500/30 text-purple-300">
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
                    className={`flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-semibold transition-all ${
                      isActive
                        ? "bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md shadow-purple-600/20"
                        : "text-slate-300 hover:bg-slate-800 hover:text-white"
                    }`}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Bottom user card & logout */}
          <div className="border-t border-slate-800 p-4">
            <div className="mb-3 rounded-xl bg-slate-900 p-3 border border-slate-800">
              <p className="text-xs font-semibold text-white truncate">
                {user?.full_name || "User"}
              </p>
              <p className="text-[11px] text-slate-400 truncate">{user?.email}</p>
              <p className="text-[10px] text-purple-400 font-bold mt-0.5">
                {getRoleDisplayName(user?.role)}
              </p>
            </div>

            <button
              type="button"
              onClick={handleLogout}
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs font-semibold text-slate-300 hover:bg-red-950/40 hover:text-red-300 hover:border-red-800/50 transition-colors cursor-pointer"
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
