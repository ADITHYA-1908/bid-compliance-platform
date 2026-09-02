"use client";

import React from "react";
import Link from "next/link";
import { Tender } from "@/lib/api";
import { TenderStatusBadge } from "./TenderStatusBadge";
import { formatCurrency, formatDateTime } from "@/lib/formatters";
import {
  Eye,
  Edit2,
  Archive,
  ChevronLeft,
  ChevronRight,
  PlusCircle,
  FileText,
  AlertCircle,
} from "lucide-react";

interface TenderTableProps {
  tenders: Tender[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  isLoading: boolean;
  error: string | null;
  onPageChange: (newPage: number) => void;
  onArchiveClick: (tender: Tender) => void;
  onRetry?: () => void;
}

export function TenderTable({
  tenders,
  page,
  pageSize,
  total,
  totalPages,
  isLoading,
  error,
  onPageChange,
  onArchiveClick,
  onRetry,
}: TenderTableProps) {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-slate-200 rounded w-1/4 mb-6"></div>
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-center justify-between py-3 border-b border-slate-100">
              <div className="space-y-2 w-1/3">
                <div className="h-3.5 bg-slate-200 rounded w-3/4"></div>
                <div className="h-3 bg-slate-100 rounded w-1/2"></div>
              </div>
              <div className="h-3 bg-slate-100 rounded w-1/6"></div>
              <div className="h-3 bg-slate-100 rounded w-1/6"></div>
              <div className="h-6 bg-slate-200 rounded-full w-20"></div>
              <div className="h-7 bg-slate-200 rounded w-16"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-white p-8 text-center shadow-xs">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-red-600 mb-3">
          <AlertCircle className="h-6 w-6" />
        </div>
        <h3 className="text-sm font-bold text-slate-900">Unable to load tenders</h3>
        <p className="text-xs text-slate-600 mt-1 max-w-md mx-auto">{error}</p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-purple-900 px-4 py-2 text-xs font-semibold text-white hover:bg-purple-800 transition-colors cursor-pointer"
          >
            Retry Request
          </button>
        )}
      </div>
    );
  }

  if (tenders.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-xs">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-purple-50 text-purple-900 mb-3">
          <FileText className="h-6 w-6" />
        </div>
        <h3 className="text-sm font-bold text-slate-900">No tenders found</h3>
        <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
          No procurement tenders match your current filter criteria, or no tenders have been drafted yet.
        </p>
        <div className="mt-5">
          <Link
            href="/procurement/tenders/new"
            className="inline-flex items-center gap-1.5 rounded-lg bg-purple-900 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-purple-800 transition-colors"
          >
            <PlusCircle className="h-4 w-4" />
            Create First Tender
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Desktop Table View */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider">
              <tr>
                <th scope="col" className="px-5 py-3.5">
                  Tender Number & Title
                </th>
                <th scope="col" className="px-4 py-3.5">
                  Department & Category
                </th>
                <th scope="col" className="px-4 py-3.5">
                  Type
                </th>
                <th scope="col" className="px-4 py-3.5">
                  Estimated Value
                </th>
                <th scope="col" className="px-4 py-3.5">
                  Status
                </th>
                <th scope="col" className="px-4 py-3.5">
                  Submission Deadline
                </th>
                <th scope="col" className="px-5 py-3.5 text-right">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white text-slate-700">
              {tenders.map((tender) => {
                const isDraft = tender.status === "DRAFT" && tender.is_active;
                const isArchived = !tender.is_active || tender.status === "ARCHIVED";
                const canArchive =
                  !isArchived &&
                  (tender.allowed_transitions
                    ? tender.allowed_transitions.includes("ARCHIVED")
                    : tender.status !== "OPEN");

                return (
                  <tr
                    key={tender.id}
                    className="hover:bg-slate-50/75 transition-colors group"
                  >
                    <td className="px-5 py-4 max-w-xs sm:max-w-sm">
                      <div className="font-mono text-xs font-bold text-slate-900">
                        <Link
                          href={`/procurement/tenders/${tender.id}`}
                          className="hover:text-purple-900 hover:underline"
                        >
                          {tender.tender_number}
                        </Link>
                      </div>
                      <div className="text-xs text-slate-600 font-medium line-clamp-1 mt-0.5" title={tender.title}>
                        {tender.title}
                      </div>
                    </td>

                    <td className="px-4 py-4 whitespace-nowrap">
                      <div className="text-slate-900 font-medium">{tender.department || "—"}</div>
                      <div className="text-[11px] text-slate-500">{tender.category || "—"}</div>
                    </td>

                    <td className="px-4 py-4 whitespace-nowrap">
                      <span className="inline-flex rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-700 uppercase">
                        {tender.procurement_type || "GOODS"}
                      </span>
                    </td>

                    <td className="px-4 py-4 whitespace-nowrap font-mono font-semibold text-slate-900">
                      {formatCurrency(tender.estimated_value, tender.currency)}
                    </td>

                    <td className="px-4 py-4 whitespace-nowrap">
                      <TenderStatusBadge status={tender.status} />
                    </td>

                    <td className="px-4 py-4 whitespace-nowrap text-slate-600 text-[11px]">
                      {formatDateTime(tender.submission_end_date)}
                    </td>

                    <td className="px-5 py-4 whitespace-nowrap text-right">
                      <div className="inline-flex items-center gap-1.5 justify-end">
                        <Link
                          href={`/procurement/tenders/${tender.id}`}
                          className="rounded-md p-1.5 text-slate-500 hover:bg-purple-50 hover:text-purple-900 transition-colors"
                          title="View Tender Details"
                        >
                          <Eye className="h-4 w-4" />
                        </Link>

                        {isDraft && (
                          <Link
                            href={`/procurement/tenders/${tender.id}/edit`}
                            className="rounded-md p-1.5 text-slate-500 hover:bg-purple-50 hover:text-purple-900 transition-colors"
                            title="Edit Tender"
                          >
                            <Edit2 className="h-4 w-4" />
                          </Link>
                        )}

                        {canArchive && (
                          <button
                            type="button"
                            onClick={() => onArchiveClick(tender)}
                            className="rounded-md p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600 transition-colors cursor-pointer"
                            title="Archive Tender"
                          >
                            <Archive className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-slate-200 px-5 py-3.5 bg-slate-50/50">
          <div className="text-xs text-slate-500">
            Showing <span className="font-semibold text-slate-800">{tenders.length}</span> of{" "}
            <span className="font-semibold text-slate-800">{total}</span> tenders • Page{" "}
            <span className="font-semibold text-slate-800">{page}</span> of{" "}
            <span className="font-semibold text-slate-800">{totalPages}</span>
          </div>

          <div className="inline-flex items-center gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 disabled:opacity-40 transition-colors cursor-pointer"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Previous
            </button>

            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 disabled:opacity-40 transition-colors cursor-pointer"
            >
              Next
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
