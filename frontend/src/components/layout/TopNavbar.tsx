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
    <header className="navbar-gradient-border sticky top-0 z-20 flex h-16 shrink-0 items-center justify-between border-b border-cyan-500/15 bg-[#040711]/85 backdrop-blur-xl px-4 sm:px-6 lg:px-8">
      <div className="flex items-center gap-3">
        {/* Mobile Hamburger Toggle */}
        <button
          type="button"
          onClick={onOpenMobileMenu}
          className="rounded-md p-1.5 text-slate-300 hover:bg-slate-800 hover:text-white lg:hidden cursor-pointer transition-colors"
          aria-label="Open mobile navigation menu"
        >
          <Menu className="h-6 w-6" />
        </button>

        <div className="hidden sm:flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
          <span>GeM Procurement Portal</span>
          <span>•</span>
          <span className="gradient-text-cyan font-bold tracking-normal">Bid Compliance Platform</span>
        </div>
      </div>

      {/* User Profile & Menu */}
      <div className="relative" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="avatar-ring flex items-center gap-3 rounded-full p-1.5 text-left text-sm hover:bg-slate-900/80 transition-all cursor-pointer border border-transparent hover:border-cyan-500/30"
          aria-expanded={dropdownOpen}
          aria-haspopup="true"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-tr from-cyan-600 to-emerald-500 text-xs font-bold text-white shadow-md glow-cyan">
            {getInitials(user?.full_name)}
          </div>

          <div className="hidden md:flex flex-col text-left">
            <span className="text-xs font-bold text-slate-100 line-clamp-1">
              {user?.full_name || "User"}
            </span>
            <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider">
              {user?.role || "BIDDER"}
            </span>
          </div>

          <ChevronDown className="hidden md:block h-3.5 w-3.5 text-slate-400" />
        </button>

        {/* Dropdown Menu */}
        {dropdownOpen && (
          <div
            className="dropdown-animate absolute right-0 mt-2 w-56 rounded-2xl border border-cyan-500/20 bg-[#060a17]/95 backdrop-blur-2xl py-2 shadow-2xl ring-1 ring-white/10 focus:outline-none z-30"
            role="menu"
          >
            <div className="border-b border-cyan-500/15 px-4 py-2.5">
              <p className="text-xs font-bold text-white">{user?.full_name}</p>
              <p className="text-[11px] text-slate-300 truncate">{user?.email}</p>
              <div className="mt-1.5">
                <span className="inline-flex items-center rounded-lg bg-cyan-950/80 border border-cyan-500/30 px-2 py-0.5 text-[10px] font-bold text-cyan-300 shadow-sm">
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
