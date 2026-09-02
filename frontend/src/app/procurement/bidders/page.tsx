"use client";

import React, { useEffect, useState, useCallback } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { BulkEvaluationModal } from "@/components/procurement/BulkEvaluationModal";
import { getTendersList } from "@/lib/api/tenders";
import { Tender } from "@/types/tender";
import {
  getActiveTenderBulkEvaluation,
  getBulkEvaluationItems,
} from "@/lib/api/bulk_evaluation";
import {
  BulkEvaluationJobStatusResponse,
  BulkEvaluationJobItem,
} from "@/types/bulk_evaluation";
import {
  Building2,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  ShieldAlert,
  Play,
  Search,
  Filter,
  Users,
  FileText,
  Clock,
  CheckSquare,
  RefreshCw,
  Eye,
  Loader2,
} from "lucide-react";

export default function ProcurementBiddersPage() {
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [selectedTenderId, setSelectedTenderId] = useState<string>("");
  const [activeJob, setActiveJob] = useState<BulkEvaluationJobStatusResponse | null>(null);
  const [items, setItems] = useState<BulkEvaluationJobItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [itemsLoading, setItemsLoading] = useState<boolean>(false);
  const [bulkModalOpen, setBulkModalOpen] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  const loadTenders = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getTendersList({ page: 1, page_size: 50 });
      const tenderItems = res.items || [];
      setTenders(tenderItems);
      if (tenderItems.length > 0) {
        const bench = tenderItems.find((t: Tender) => t.tender_number === "GEM/2026/B/200000") || tenderItems[0];
        setSelectedTenderId(bench.id);
      }
    } catch (err: any) {
      console.error("Failed to load tenders:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTenders();
  }, [loadTenders]);

  const loadBidders = useCallback(async (tId: string) => {
    if (!tId) return;
    try {
      setItemsLoading(true);
      const job = await getActiveTenderBulkEvaluation(tId);
      setActiveJob(job);
      if (job) {
        const res = await getBulkEvaluationItems(job.id, statusFilter || undefined, 1, 50);
        setItems(res.items);
      } else {
        setItems([]);
      }
    } catch (err: any) {
      console.error("Failed to load bidders:", err);
    } finally {
      setItemsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    if (selectedTenderId) {
      loadBidders(selectedTenderId);
    }
  }, [selectedTenderId, loadBidders]);

  const selectedTender = tenders.find((t) => t.id === selectedTenderId);

  return (
    <DashboardLayout
      allowedRoles={["PROCUREMENT_OFFICER", "ADMIN"]}
      title="Participating Bidders & Bulk Verification Hub"
      description="View vendor submissions, run one-operation verification across hundreds of bidders, and inspect statutory compliance records."
      breadcrumbs={[
        { label: "Procurement", href: "/procurement" },
        { label: "Bidders Directory" },
      ]}
    >
      <div className="space-y-6">
        {/* Banner & Batch Action Bar */}
        <div className="rounded-2xl bg-white border border-slate-200 p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-purple-100 text-purple-700 font-bold">
              <Users className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-lg font-black text-slate-900">
                Bidder Dossiers & High-Volume Operations
              </h2>
              <p className="text-xs text-slate-500">
                Select a tender to inspect all vendor submissions or launch instant single-operation batch verification.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <select
              value={selectedTenderId}
              onChange={(e) => setSelectedTenderId(e.target.value)}
              className="rounded-xl border border-slate-300 bg-slate-50 text-xs font-bold text-slate-800 px-3 py-2.5 focus:ring-2 focus:ring-purple-500 focus:outline-hidden"
            >
              {tenders.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.tender_number} • {t.title.substring(0, 30)}...
                </option>
              ))}
            </select>

            <button
              onClick={() => setBulkModalOpen(true)}
              disabled={!selectedTenderId}
              className="inline-flex items-center gap-2 rounded-xl bg-purple-900 hover:bg-purple-800 text-white font-bold text-xs px-4 py-2.5 shadow-md transition-all disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              Verify All Bidders
            </button>
          </div>
        </div>

        {/* Bidders Directory Table */}
        <div className="rounded-2xl bg-white border border-slate-200 shadow-sm overflow-hidden space-y-4">
          <div className="p-6 border-b border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Vendor Roster for Tender {selectedTender?.tender_number || ""}
              </h3>
              <p className="text-xs text-slate-500">
                {items.length} participating vendors loaded
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Filter by vendor name or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="rounded-xl border border-slate-300 pl-9 pr-4 py-2 text-xs focus:ring-2 focus:ring-purple-500 focus:outline-hidden"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700"
              >
                <option value="">All Statuses</option>
                <option value="SUCCESS">SUCCESS (PASS)</option>
                <option value="REVIEW_REQUIRED">REVIEW REQUIRED</option>
                <option value="FAILED">FAILED</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-[10px] uppercase font-bold text-slate-500 border-y border-slate-200">
                <tr>
                  <th className="px-6 py-3">Vendor / Organization</th>
                  <th className="px-6 py-3">Bid Number</th>
                  <th className="px-6 py-3">Pipeline Stage</th>
                  <th className="px-6 py-3">Verification Outcome</th>
                  <th className="px-6 py-3">Score & Risk</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {itemsLoading ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-400">
                      <Loader2 className="h-6 w-6 animate-spin mx-auto text-purple-600 mb-2" />
                      Loading bidders list...
                    </td>
                  </tr>
                ) : items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-400">
                      No bidder items found. Click <strong>"Verify All Bidders"</strong> to initialize batch run.
                    </td>
                  </tr>
                ) : (
                  items
                    .filter((it) => {
                      if (!searchQuery) return true;
                      const q = searchQuery.toLowerCase();
                      return (
                        (it.bidder_name && it.bidder_name.toLowerCase().includes(q)) ||
                        (it.bid_number && it.bid_number.toLowerCase().includes(q))
                      );
                    })
                    .map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <Building2 className="h-4 w-4 text-slate-400 shrink-0" />
                            <div>
                              <p className="font-bold text-slate-900">{item.bidder_name || "Vendor Organization"}</p>
                              <p className="text-[10px] text-slate-400">Statutory Dossier Attached</p>
                            </div>
                          </div>
                        </td>

                        <td className="px-6 py-4 font-mono font-bold text-slate-800">
                          {item.bid_number}
                        </td>

                        <td className="px-6 py-4">
                          <span className="inline-flex items-center rounded-md bg-purple-50 px-2 py-0.5 text-[10px] font-semibold text-purple-800 border border-purple-200">
                            {item.current_stage}
                          </span>
                        </td>

                        <td className="px-6 py-4">
                          {item.status === "SUCCESS" ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[10px] font-bold text-emerald-800 border border-emerald-200">
                              <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                              PASS
                            </span>
                          ) : item.status === "REVIEW_REQUIRED" ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-[10px] font-bold text-amber-800 border border-amber-200">
                              <AlertCircle className="h-3 w-3 text-amber-600" />
                              REVIEW
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2.5 py-0.5 text-[10px] font-bold text-rose-800 border border-rose-200">
                              <AlertTriangle className="h-3 w-3 text-rose-600" />
                              FAIL
                            </span>
                          )}
                        </td>

                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold text-slate-800">
                              {item.final_score ? `${item.final_score}/100` : "N/A"}
                            </span>
                            <span className="text-[10px] font-bold text-slate-500 uppercase">
                              {item.risk_level}
                            </span>
                          </div>
                        </td>

                        <td className="px-6 py-4 text-right">
                          <button
                            onClick={() => setBulkModalOpen(true)}
                            className="inline-flex items-center gap-1 text-purple-700 hover:text-purple-900 font-bold text-xs"
                          >
                            <Eye className="h-3.5 w-3.5" />
                            Inspect Dossier
                          </button>
                        </td>
                      </tr>
                    ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {selectedTenderId && (
        <BulkEvaluationModal
          tenderId={selectedTenderId}
          tenderNumber={selectedTender?.tender_number}
          tenderTitle={selectedTender?.title}
          isOpen={bulkModalOpen}
          onClose={() => setBulkModalOpen(false)}
          onJobCompleted={() => {
            if (selectedTenderId) loadBidders(selectedTenderId);
          }}
        />
      )}
    </DashboardLayout>
  );
}
