"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Menu, LogOut, User as UserIcon, Shield, ChevronDown } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { getRoleDisplayName } from "@/lib/roles";

interface TopNavbarProps {
  onOpenMobileMenu: () => void;
}

export function TopNavbar({ onOpenMobileMenu }: TopNavbarProps) {
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
    <header className="glass-header-light sticky top-0 z-20 flex h-18 shrink-0 items-center justify-between border-b border-slate-200 px-4 sm:px-6 lg:px-8">
      <div className="flex items-center gap-3">
        {/* Mobile Hamburger Toggle */}
        <button
          type="button"
          onClick={onOpenMobileMenu}
          className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-100 hover:text-slate-900 lg:hidden cursor-pointer transition-colors"
          aria-label="Open mobile navigation menu"
        >
          <Menu className="h-6 w-6" />
        </button>

        <div className="hidden sm:flex items-center gap-2.5 text-xs font-bold uppercase tracking-wider text-slate-500 font-heading">
          <span>GeM Procurement Portal</span>
          <span>•</span>
          <span className="text-emerald-700 font-bold tracking-normal flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 status-indicator-pulse inline-block" />
            Bid Compliance Suite
          </span>
        </div>
      </div>

      {/* User Profile & Menu */}
      <div className="relative" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="flex items-center gap-3 rounded-full p-1.5 text-left text-sm hover:bg-slate-100/80 transition-all cursor-pointer border border-transparent hover:border-slate-200"
          aria-expanded={dropdownOpen}
          aria-haspopup="true"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-600 text-xs font-bold text-white shadow-xs">
            {getInitials(user?.full_name)}
          </div>

          <div className="hidden md:flex flex-col text-left">
            <span className="text-xs font-bold text-slate-900 line-clamp-1">
              {user?.full_name || "User"}
            </span>
            <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider font-heading">
              {user?.role || "BIDDER"}
            </span>
          </div>

          <ChevronDown className="hidden md:block h-3.5 w-3.5 text-slate-500" />
        </button>

        {/* Dropdown Menu */}
        {dropdownOpen && (
          <div
            className="dropdown-animate absolute right-0 mt-2 w-56 rounded-2xl border border-slate-200 bg-white/95 backdrop-blur-2xl py-2 shadow-xl ring-1 ring-black/5 focus:outline-none z-30"
            role="menu"
          >
            <div className="border-b border-slate-100 px-4 py-2.5">
              <p className="text-xs font-bold text-slate-900">{user?.full_name}</p>
              <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
              <div className="mt-1.5">
                <span className="inline-flex items-center rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[10px] font-bold text-emerald-800 shadow-2xs">
                  {getRoleDisplayName(user?.role)}
                </span>
              </div>
            </div>

            <div className="py-1">
              <Link
                href="/account"
                onClick={() => setDropdownOpen(false)}
                className="flex items-center gap-2.5 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800/80 hover:text-white transition-colors"
                role="menuitem"
              >
                <UserIcon className="h-4 w-4 text-purple-400" />
                Account & Security
              </Link>
            </div>

            <div className="border-t border-slate-800/80 pt-1">
              <button
                type="button"
                onClick={handleLogout}
                className="flex w-full items-center gap-2.5 px-4 py-2 text-xs font-medium text-red-400 hover:bg-red-950/50 hover:text-red-300 cursor-pointer transition-colors"
                role="menuitem"
              >
                <LogOut className="h-4 w-4 text-red-400" />
                Sign Out
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
