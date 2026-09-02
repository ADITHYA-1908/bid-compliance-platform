"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Bell,
  CheckCheck,
  ExternalLink,
  AlertTriangle,
  CheckCircle2,
  Info,
  ShieldAlert,
  Clock,
  ChevronRight,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { notificationApi } from "@/lib/api/notifications";
import { NotificationItem, NotificationSeverity } from "@/types/notification";

export function NotificationBell() {
  const router = useRouter();
  const { user } = useAuth();
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [recentNotifications, setRecentNotifications] = useState<NotificationItem[]>([]);
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Fetch unread count
  const fetchUnreadCount = useCallback(async () => {
    if (!user) return;
    try {
      const res = await notificationApi.getUnreadCount();
      setUnreadCount(res.unread_count || 0);
    } catch {
      // Benign background polling error
    }
  }, [user]);

  // Fetch recent preview items
  const fetchRecent = useCallback(async () => {
    if (!user) return;
    setIsLoading(true);
    try {
      const res = await notificationApi.getNotifications({ page: 1, page_size: 6 });
      setRecentNotifications(res.items || []);
      setUnreadCount(res.unread_count || 0);
    } catch {
      // Ignore
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  // Polling unread count every 30s
  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  // Open popover handler
  const handleToggle = () => {
    if (!isOpen) {
      fetchRecent();
    }
    setIsOpen((prev) => !prev);
  };

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Mark single as read
  const handleItemClick = async (notif: NotificationItem) => {
    if (!notif.is_read) {
      try {
        await notificationApi.markAsRead(notif.id);
        setRecentNotifications((prev) =>
          prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
        );
        setUnreadCount((prev) => Math.max(0, prev - 1));
      } catch {
        // Ignore
      }
    }
    setIsOpen(false);
    if (notif.action_url) {
      router.push(notif.action_url);
    }
  };

  // Mark all as read
  const handleMarkAllRead = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const res = await notificationApi.markAllAsRead();
      setRecentNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(res.unread_count || 0);
    } catch {
      // Ignore
    }
  };

  // Format relative time
  const formatTime = (iso: string) => {
    try {
      const d = new Date(iso);
      const diff = Math.floor((Date.now() - d.getTime()) / 1000);
      if (diff < 60) return "just now";
      if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
      if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
      return `${Math.floor(diff / 86400)}d ago`;
    } catch {
      return "";
    }
  };

  const getSeverityIcon = (sev: NotificationSeverity) => {
    switch (sev) {
      case "CRITICAL":
        return <ShieldAlert className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />;
      case "WARNING":
        return <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />;
      case "SUCCESS":
        return <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />;
      case "INFO":
      default:
        return <Info className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />;
    }
  };

  return (
    <div className="relative" ref={popoverRef}>
      <button
        type="button"
        onClick={handleToggle}
        className="relative rounded-full p-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors cursor-pointer"
        aria-label="Open notifications"
        aria-expanded={isOpen}
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-bold text-white shadow-xs">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* Popover Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-xl border border-slate-200 bg-white shadow-2xl ring-1 ring-black/5 z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/75 px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-slate-900">Notifications</span>
              {unreadCount > 0 && (
                <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-800">
                  {unreadCount} unread
                </span>
              )}
            </div>

            {unreadCount > 0 && (
              <button
                type="button"
                onClick={handleMarkAllRead}
                className="flex items-center gap-1 text-[11px] font-semibold text-blue-900 hover:text-blue-700 cursor-pointer"
              >
                <CheckCheck className="h-3.5 w-3.5" />
                Mark all read
              </button>
            )}
          </div>

          {/* List */}
          <div className="max-h-[380px] overflow-y-auto divide-y divide-slate-100">
            {isLoading && recentNotifications.length === 0 ? (
              <div className="flex items-center justify-center py-10 text-xs text-slate-400">
                Loading notifications...
              </div>
            ) : recentNotifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400 mb-2">
                  <Bell className="h-5 w-5" />
                </div>
                <p className="text-xs font-semibold text-slate-700">No notifications yet</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  You are all caught up on submissions, reviews, and alerts.
                </p>
              </div>
            ) : (
              recentNotifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => handleItemClick(n)}
                  className={`group flex items-start gap-3 p-3.5 text-left transition-colors cursor-pointer ${
                    !n.is_read
                      ? "bg-blue-50/40 hover:bg-blue-50/70"
                      : "bg-white hover:bg-slate-50"
                  }`}
                >
                  {getSeverityIcon(n.severity)}

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1 mb-0.5">
                      <p
                        className={`text-xs truncate ${
                          !n.is_read ? "font-bold text-slate-900" : "font-medium text-slate-800"
                        }`}
                      >
                        {n.title}
                      </p>
                      {!n.is_read && (
                        <span className="h-2 w-2 rounded-full bg-blue-600 shrink-0" />
                      )}
                    </div>

                    <p className="text-[11px] text-slate-600 line-clamp-2 leading-relaxed">
                      {n.message}
                    </p>

                    <div className="flex items-center justify-between mt-2 pt-1 text-[10px] text-slate-400 border-t border-slate-100/60">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatTime(n.created_at)}
                      </span>

                      {n.action_url && (
                        <span className="flex items-center gap-0.5 text-blue-900 font-semibold group-hover:underline">
                          View details
                          <ChevronRight className="h-3 w-3" />
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-slate-100 bg-slate-50/90 p-2.5 text-center">
            <Link
              href="/notifications"
              onClick={() => setIsOpen(false)}
              className="inline-flex items-center justify-center gap-1.5 w-full rounded-lg py-1.5 text-xs font-semibold text-blue-900 hover:bg-blue-50 transition-colors"
            >
              <span>Open Notification Center</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
