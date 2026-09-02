"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Menu, LogOut, User as UserIcon, Shield, ChevronDown } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { getRoleDisplayName } from "@/lib/roles";
import { NotificationBell } from "@/components/layout/NotificationBell";

export function TopNavbar({ onOpenMobileMenu }: { onOpenMobileMenu: () => void }) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const getInitials = (name?: string) => {
    if (!name) return "U";
    const parts = name.trim().split(" ");
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  };

  return (
    <header className="sticky top-0 z-20 flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6 lg:px-8">
      <div className="flex items-center gap-3">
        {/* Mobile Hamburger Toggle */}
        <button
          type="button"
          onClick={onOpenMobileMenu}
          className="rounded-md p-1.5 text-slate-600 hover:bg-slate-100 lg:hidden cursor-pointer"
          aria-label="Open mobile navigation menu"
        >
          <Menu className="h-6 w-6" />
        </button>

        <div className="hidden sm:flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
          <span>GeM Procurement Portal</span>
          <span>•</span>
          <span className="text-blue-900 font-bold">Bid Compliance Platform</span>
        </div>
      </div>

      {/* Right Controls: Notifications & User Profile */}
      <div className="flex items-center gap-2 sm:gap-4">
        <NotificationBell />

        <div className="relative" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="flex items-center gap-3 rounded-full p-1 text-left text-sm hover:bg-slate-50 transition-colors cursor-pointer"
          aria-expanded={dropdownOpen}
          aria-haspopup="true"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-900 text-xs font-bold text-white shadow-xs">
            {getInitials(user?.full_name)}
          </div>

          <div className="hidden md:flex flex-col text-left">
            <span className="text-xs font-semibold text-slate-900 line-clamp-1">
              {user?.full_name || "User"}
            </span>
            <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">
              {user?.role || "BIDDER"}
            </span>
          </div>

          <ChevronDown className="hidden md:block h-3.5 w-3.5 text-slate-400" />
        </button>

        {/* Dropdown Menu */}
        {dropdownOpen && (
          <div
            className="absolute right-0 mt-2 w-56 rounded-lg border border-slate-200 bg-white py-1.5 shadow-lg ring-1 ring-black/5 focus:outline-none z-30"
            role="menu"
          >
            <div className="border-b border-slate-100 px-4 py-2.5">
              <p className="text-xs font-semibold text-slate-900">{user?.full_name}</p>
              <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
              <div className="mt-1.5">
                <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-700">
                  {getRoleDisplayName(user?.role)}
                </span>
              </div>
            </div>

            <div className="py-1">
              <Link
                href="/account"
                onClick={() => setDropdownOpen(false)}
                className="flex items-center gap-2.5 px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-slate-900"
                role="menuitem"
              >
                <UserIcon className="h-4 w-4 text-slate-400" />
                Account & Security
              </Link>
            </div>

            <div className="border-t border-slate-100 pt-1">
              <button
                type="button"
                onClick={handleLogout}
                className="flex w-full items-center gap-2.5 px-4 py-2 text-xs font-medium text-red-600 hover:bg-red-50 hover:text-red-700 cursor-pointer"
                role="menuitem"
              >
                <LogOut className="h-4 w-4 text-red-500" />
                Sign Out
              </button>
            </div>
          </div>
        )}
      </div>
      </div>
    </header>
  );
}
