"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Bell,
  CheckCheck,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Info,
  Clock,
  Filter,
  Search,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  RefreshCw,
  MailCheck,
  Mail,
  ShieldCheck,
} from "lucide-react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import { notificationApi } from "@/lib/api/notifications";
import {
  NotificationItem,
  NotificationListResponse,
  NotificationSeverity,
} from "@/types/notification";

export default function NotificationCenterPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();

  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize] = useState<number>(15);

  const [activeTab, setActiveTab] = useState<string>("ALL"); // ALL, UNREAD, CRITICAL, WARNING, SUCCESS, INFO
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchNotifications = useCallback(
    async (page: number = 1, showRefreshSpinner: boolean = false) => {
      if (!user) return;
      if (showRefreshSpinner) setIsRefreshing(true);
      else setIsLoading(true);
      setError(null);

      try {
        let isReadParam: boolean | undefined = undefined;
        let severityParam: string | undefined = undefined;

        if (activeTab === "UNREAD") {
          isReadParam = false;
        } else if (["CRITICAL", "WARNING", "SUCCESS", "INFO"].includes(activeTab)) {
          severityParam = activeTab;
        }

        const res: NotificationListResponse = await notificationApi.getNotifications({
          page,
          page_size: pageSize,
          is_read: isReadParam,
          severity: severityParam,
          notification_type: typeFilter || undefined,
          search: searchQuery.trim() || undefined,
        });

        setNotifications(res.items || []);
        setTotalCount(res.total || 0);
        setUnreadCount(res.unread_count || 0);
        setTotalPages(res.total_pages || 1);
        setCurrentPage(res.page || 1);
      } catch (err: any) {
        setError(err.message || "Failed to load notifications. Please try again.");
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [user, activeTab, typeFilter, searchQuery, pageSize]
  );

  useEffect(() => {
    fetchNotifications(1);
  }, [fetchNotifications]);

  const handleMarkAsRead = async (id: string) => {
    try {
      await notificationApi.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // Ignore
    }
  };

  const handleMarkAsUnread = async (id: string) => {
    try {
      await notificationApi.markAsUnread(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: false, read_at: null } : n))
      );
      setUnreadCount((prev) => prev + 1);
    } catch {
      // Ignore
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      const res = await notificationApi.markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(res.unread_count || 0);
    } catch {
      // Ignore
    }
  };

  const formatTime = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  const getSeverityBadge = (sev: NotificationSeverity) => {
    switch (sev) {
      case "CRITICAL":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-red-50 px-2 py-0.5 text-xs font-bold text-red-700 border border-red-200">
            <ShieldAlert className="h-3.5 w-3.5 text-red-600" />
            CRITICAL
          </span>
        );
      case "WARNING":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-0.5 text-xs font-bold text-amber-700 border border-amber-200">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
            WARNING
          </span>
        );
      case "SUCCESS":
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-bold text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
            SUCCESS
          </span>
        );
      case "INFO":
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2 py-0.5 text-xs font-bold text-blue-700 border border-blue-200">
            <Info className="h-3.5 w-3.5 text-blue-600" />
            INFO
          </span>
        );
    }
  };

  return (
    <DashboardLayout
      allowedRoles={["BIDDER", "PROCUREMENT_OFFICER", "ADMIN"]}
      title="Notification Center"
      description="Real-time alerts, verification outcomes, quality warnings, and deadline reminders"
      breadcrumbs={[{ label: "Notifications" }]}
    >
      <div className="space-y-6 pb-12">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-900 text-white shadow-xs">
                <Bell className="h-5 w-5" />
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight text-slate-900">
                  Notification Center
                </h1>
                <p className="text-xs text-slate-500">
                  Real-time alerts, verification outcomes, quality warnings, and deadline reminders
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => fetchNotifications(currentPage, true)}
              disabled={isRefreshing}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`h-3.5 w-3.5 text-slate-500 ${isRefreshing ? "animate-spin" : ""}`} />
              Refresh
            </button>

            {unreadCount > 0 && (
              <button
                type="button"
                onClick={handleMarkAllAsRead}
                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-blue-800 transition-colors shadow-xs cursor-pointer"
              >
                <CheckCheck className="h-3.5 w-3.5" />
                Mark All as Read ({unreadCount})
              </button>
            )}
          </div>
        </div>

        {/* Filter Bar & Search */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1 border border-slate-200/70">
            {[
              { id: "ALL", label: "All", count: totalCount },
              { id: "UNREAD", label: "Unread", count: unreadCount },
              { id: "CRITICAL", label: "Critical" },
              { id: "WARNING", label: "Warnings" },
              { id: "SUCCESS", label: "Success" },
              { id: "INFO", label: "Info" },
            ].map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => {
                    setActiveTab(tab.id);
                    setCurrentPage(1);
                  }}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer whitespace-nowrap ${
                    isActive
                      ? "bg-white text-slate-900 shadow-xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-white/50"
                  }`}
                >
                  <span>{tab.label}</span>
                  {tab.count !== undefined && (
                    <span
                      className={`rounded-full px-1.5 py-0.2 text-[10px] font-bold ${
                        isActive
                          ? "bg-blue-100 text-blue-900"
                          : "bg-slate-200 text-slate-700"
                      }`}
                    >
                      {tab.count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Search & Type Filters */}
          <div className="flex items-center gap-2">
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search notifications..."
                className="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-8 pr-3 text-xs text-slate-900 focus:border-blue-900 focus:outline-hidden focus:ring-1 focus:ring-blue-900"
              />
            </div>

            <select
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="rounded-lg border border-slate-200 bg-white py-1.5 px-3 text-xs text-slate-700 focus:border-blue-900 focus:outline-hidden"
            >
              <option value="">All Categories</option>
              <option value="BID_SUBMITTED">Bid Submitted</option>
              <option value="DOCUMENT_QUALITY_REVIEW_REQUIRED">Document Quality</option>
              <option value="DUPLICATE_DOCUMENT_ALERT">Duplicate / Reuse Alert</option>
              <option value="VERIFICATION_REVIEW_REQUIRED">Human Review Required</option>
              <option value="BULK_EVALUATION_COMPLETED">Bulk Evaluation</option>
              <option value="TENDER_DEADLINE_APPROACHING">Tender Deadline</option>
              <option value="CERTIFICATE_EXPIRING">Certificate Expiry</option>
              <option value="FINAL_DECISION_RECORDED">Final Decision</option>
            </select>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs font-medium text-red-800 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Notification List */}
        {isLoading ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-blue-900 border-r-transparent mb-3" />
            <p className="text-xs font-semibold text-slate-600">Loading notifications...</p>
          </div>
        ) : notifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white py-16 px-4 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-900 mb-3 shadow-2xs">
              <ShieldCheck className="h-7 w-7" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">No notifications found</h3>
            <p className="text-xs text-slate-500 max-w-sm mt-1">
              There are no notifications matching your current filters. Check back later or adjust your filter criteria.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {notifications.map((n) => {
              const isUnread = !n.is_read;
              return (
                <div
                  key={n.id}
                  className={`rounded-xl border p-4 sm:p-5 transition-all shadow-2xs ${
                    isUnread
                      ? "border-blue-200 bg-blue-50/20 hover:border-blue-300"
                      : "border-slate-200 bg-white hover:border-slate-300"
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className="pt-0.5">{getSeverityBadge(n.severity)}</div>

                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <h4
                            className={`text-sm tracking-tight ${
                              isUnread ? "font-bold text-slate-900" : "font-semibold text-slate-800"
                            }`}
                          >
                            {n.title}
                          </h4>
                          {isUnread && (
                            <span className="h-2 w-2 rounded-full bg-blue-600 shrink-0" />
                          )}
                        </div>

                        <p className="text-xs text-slate-600 leading-relaxed max-w-3xl">
                          {n.message}
                        </p>

                        <div className="flex flex-wrap items-center gap-3 pt-1.5 text-[11px] text-slate-400">
                          <span className="flex items-center gap-1 font-medium">
                            <Clock className="h-3 w-3" />
                            {formatTime(n.created_at)}
                          </span>

                          <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-600">
                            {n.notification_type}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 self-end sm:self-start shrink-0 pt-2 sm:pt-0">
                      {isUnread ? (
                        <button
                          type="button"
                          onClick={() => handleMarkAsRead(n.id)}
                          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer"
                          title="Mark as read"
                        >
                          <MailCheck className="h-3.5 w-3.5 text-blue-900" />
                          <span>Mark Read</span>
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleMarkAsUnread(n.id)}
                          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-500 hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer"
                          title="Mark as unread"
                        >
                          <Mail className="h-3.5 w-3.5 text-slate-400" />
                          <span>Mark Unread</span>
                        </button>
                      )}

                      {n.action_url && (
                        <button
                          type="button"
                          onClick={() => router.push(n.action_url!)}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-800 transition-colors shadow-xs cursor-pointer"
                        >
                          <span>View</span>
                          <ExternalLink className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-200 pt-4">
            <p className="text-xs text-slate-500">
              Showing page <span className="font-bold text-slate-900">{currentPage}</span> of{" "}
              <span className="font-bold text-slate-900">{totalPages}</span> ({totalCount} total)
            </p>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => fetchNotifications(currentPage - 1)}
                disabled={currentPage <= 1 || isLoading}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition-colors shadow-2xs cursor-pointer"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                Previous
              </button>

              <button
                type="button"
                onClick={() => fetchNotifications(currentPage + 1)}
                disabled={currentPage >= totalPages || isLoading}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition-colors shadow-2xs cursor-pointer"
              >
                Next
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
