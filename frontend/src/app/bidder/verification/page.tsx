"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import {
  api,
  BidListItem,
  BidVerificationListResponse,
  VerificationSummaryItem,
} from "@/lib/api";
import {
  ShieldCheck,
  AlertTriangle,
  FileCheck,
  RotateCw,
  RefreshCw,
  Loader2,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Clock,
  Layers,
  ArrowRight,
  Info,
} from "lucide-react";

export default function BidderVerificationPage() {
  const [bids, setBids] = useState<BidListItem[]>([]);
  const [selectedBidId, setSelectedBidId] = useState<string | null>(null);
  const [verificationData, setVerificationData] = useState<BidVerificationListResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingVerifications, setLoadingVerifications] = useState<boolean>(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);

  const loadBidVerifications = React.useCallback(async (bidId: string) => {
    setLoadingVerifications(true);
    try {
      const data = await api.getBidVerifications(bidId);
      setVerificationData(data);
    } catch (err) {
      console.error("Failed to load bid verifications:", err);
      setVerificationData(null);
    } finally {
      setLoadingVerifications(false);
    }
  }, []);

  const loadBids = React.useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getMyBids();
      setBids(res.items);
      if (res.items.length > 0) {
        setSelectedBidId(res.items[0].id);
        await loadBidVerifications(res.items[0].id);
      }
    } catch (err) {
      console.error("Failed to load bids:", err);
    } finally {
      setLoading(false);
    }
  }, [loadBidVerifications]);

  useEffect(() => {
    loadBids();
  }, [loadBids]);

  const handleSelectBid = async (bidId: string) => {
    setSelectedBidId(bidId);
    await loadBidVerifications(bidId);
  };

  const handleRetry = async (vId: string) => {
    if (!selectedBidId) return;
    setRetryingId(vId);
    try {
      await api.retryVerification(selectedBidId, vId);
      await loadBidVerifications(selectedBidId);
    } catch (err) {
      alert("Failed to retry verification.");
    } finally {
      setRetryingId(null);
    }
  };

  return (
    <DashboardLayout
      allowedRoles={["BIDDER"]}
      title="Statutory Claim Verification Hub"
      description="Inspect deterministic statutory & compliance claim verification telemetry across your proposals."
      breadcrumbs={[
        { label: "Bidder Portal", href: "/bidder" },
        { label: "Verification Hub" },
      ]}
    >
      <div className="space-y-6">
        {/* Development Notice Banner */}
        <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-4 text-xs text-indigo-950 space-y-1 shadow-2xs">
          <div className="flex items-center gap-2 font-bold text-indigo-900">
            <Info className="h-4 w-4 text-indigo-700 shrink-0" />
            <span>Verification Engine Overview — Mock / Sandbox & Internal Validation (Part 5)</span>
          </div>
          <p className="text-[11px] text-indigo-800 leading-relaxed pl-6">
            All statutory (GST, PAN, Udyam, MCA), registration (Startup, NSIC, EPFO, ESIC), technical (OEM, Local Content, BIS), and integrity (Blacklisting, Debarment, Cross-Document) checks use deterministic mock registry adapters. Verification confirms claim authenticity and consistency; tender compliance rule matching (PASS/FAIL) is evaluated separately in Part 6.
          </p>
        </div>

        {/* Workspace Selector Bar */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs space-y-3">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-600">
            Select Active Bid Proposal
          </label>

          {loading ? (
            <div className="flex items-center gap-2 text-xs text-slate-500 py-2">
              <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
              <span>Loading proposal submissions...</span>
            </div>
          ) : bids.length === 0 ? (
            <p className="text-xs text-slate-500">No bid proposals created yet.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {bids.map((b) => (
                <button
                  key={b.id}
                  type="button"
                  onClick={() => handleSelectBid(b.id)}
                  className={`inline-flex items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-bold transition-all ${
                    selectedBidId === b.id
                      ? "bg-blue-700 text-white shadow-xs"
                      : "bg-slate-50 text-slate-700 hover:bg-slate-100 border border-slate-200"
                  }`}
                >
                  <FileCheck className="h-3.5 w-3.5" />
                  <span>{b.bid_number}</span>
                  <span
                    className={`text-[9px] font-bold px-1.5 py-0.2 rounded ${
                      selectedBidId === b.id
                        ? "bg-blue-800 text-blue-100"
                        : "bg-slate-200 text-slate-700"
                    }`}
                  >
                    {b.status}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Verification Summary Metrics */}
        {verificationData && (
          <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
            <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs">
              <span className="text-[10px] font-bold uppercase text-slate-400">Total Claims</span>
              <p className="text-xl font-extrabold text-slate-900 mt-1">{verificationData.total_verifications}</p>
            </div>
            <div className="rounded-xl border border-emerald-100 bg-emerald-50/50 p-3.5 shadow-2xs">
              <span className="text-[10px] font-bold uppercase text-emerald-700">Verified</span>
              <p className="text-xl font-extrabold text-emerald-700 mt-1">{verificationData.verified_count}</p>
            </div>
            <div className="rounded-xl border border-rose-100 bg-rose-50/50 p-3.5 shadow-2xs">
              <span className="text-[10px] font-bold uppercase text-rose-700">Not Verified</span>
              <p className="text-xl font-extrabold text-rose-700 mt-1">{verificationData.not_verified_count}</p>
            </div>
            <div className="rounded-xl border border-amber-100 bg-amber-50/50 p-3.5 shadow-2xs">
              <span className="text-[10px] font-bold uppercase text-amber-700">Needs Review</span>
              <p className="text-xl font-extrabold text-amber-700 mt-1">{verificationData.needs_review_count}</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 shadow-2xs">
              <span className="text-[10px] font-bold uppercase text-slate-600">Unavailable</span>
              <p className="text-xl font-extrabold text-slate-700 mt-1">{verificationData.unavailable_count}</p>
            </div>
            <div className="rounded-xl border border-red-100 bg-red-50/50 p-3.5 shadow-2xs">
              <span className="text-[10px] font-bold uppercase text-red-700">Failed</span>
              <p className="text-xl font-extrabold text-red-700 mt-1">{verificationData.failed_count}</p>
            </div>
          </div>
        )}

        {/* Verification Records List */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-indigo-700" />
              <h3 className="text-sm font-bold text-slate-900">
                Claim Verification Audit Trail
              </h3>
            </div>

            {selectedBidId && (
              <Link
                href={`/bidder/bids/${selectedBidId}`}
                className="inline-flex items-center gap-1 text-xs font-bold text-blue-700 hover:text-blue-800"
              >
                <span>Open Bid Workspace</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            )}
          </div>

          {loadingVerifications ? (
            <div className="flex flex-col items-center justify-center py-12 space-y-3">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
              <p className="text-xs text-slate-500">Retrieving verification telemetry...</p>
            </div>
          ) : verificationData && verificationData.verifications.length > 0 ? (
            <div className="space-y-3">
              {verificationData.verifications.map((v) => (
                <div
                  key={v.id}
                  className="rounded-xl border border-slate-200 bg-slate-50/40 p-4 space-y-3 shadow-2xs text-xs"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900 text-sm">
                        {v.verification_type} Claim
                      </span>
                      <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                        {v.source_name} ({v.source_type})
                      </span>
                      <span className="text-[10px] text-slate-400 font-semibold">
                        Attempt #{v.attempt_number}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                          v.verification_status === "VERIFIED"
                            ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                            : v.verification_status === "NOT_VERIFIED"
                            ? "bg-rose-50 text-rose-800 border-rose-200"
                            : v.verification_status === "NEEDS_REVIEW"
                            ? "bg-amber-50 text-amber-800 border-amber-200"
                            : v.verification_status === "UNAVAILABLE"
                            ? "bg-slate-100 text-slate-800 border-slate-300"
                            : "bg-red-100 text-red-800 border-red-300"
                        }`}
                      >
                        {v.verification_status.replace(/_/g, " ")}
                      </span>

                      {v.is_retryable && (
                        <button
                          type="button"
                          onClick={() => handleRetry(v.id)}
                          disabled={retryingId === v.id}
                          className="inline-flex items-center gap-1 text-[10px] font-bold text-indigo-700 hover:text-indigo-900 border border-indigo-200 bg-indigo-50 px-2.5 py-1 rounded-lg transition-colors disabled:opacity-50"
                        >
                          {retryingId === v.id ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <RefreshCw className="h-3 w-3" />
                          )}
                          Retry Verification
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-white p-3 rounded-lg border border-slate-200">
                    <div>
                      <span className="text-[9px] font-bold uppercase text-slate-400">Claimed Identifier</span>
                      <p className="font-mono font-bold text-slate-900 mt-0.5">{v.claimed_value}</p>
                    </div>
                    <div>
                      <span className="text-[9px] font-bold uppercase text-slate-400">Verified Match Value</span>
                      <p className="font-mono font-bold text-slate-900 mt-0.5">{v.verified_value || "—"}</p>
                    </div>
                    <div>
                      <span className="text-[9px] font-bold uppercase text-slate-400">Match Classification</span>
                      <p className="font-bold text-slate-800 mt-0.5">{v.match_status} (Conf: {Math.round(v.confidence * 100)}%)</p>
                    </div>
                  </div>

                  {/* Domain Specific Attributes */}
                  {v.evidence && (
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px] bg-slate-50/80 p-3 rounded-lg border border-slate-200">
                      {(v.evidence.legal_name || v.evidence.registry_legal_name || v.evidence.registry_name || v.evidence.registry_enterprise_name || v.evidence.company_name || v.evidence.registry_company_name || v.evidence.entity_name || v.evidence.establishment_name || v.evidence.employer_name || v.evidence.oem_name) && (
                        <div>
                          <span className="text-[9px] font-bold uppercase text-slate-400">Registry Entity / OEM</span>
                          <p className="font-bold text-slate-800 truncate">
                            {v.evidence.oem_name ? `${v.evidence.oem_name} (OEM)` : (v.evidence.registry_legal_name || v.evidence.registry_name || v.evidence.registry_enterprise_name || v.evidence.registry_company_name || v.evidence.company_name || v.evidence.entity_name || v.evidence.establishment_name || v.evidence.employer_name || v.evidence.legal_name || "—")}
                          </p>
                        </div>
                      )}

                      {v.evidence.authorized_entity && (
                        <div>
                          <span className="text-[9px] font-bold uppercase text-slate-400">Authorized Bidder / Grantee</span>
                          <p className="font-bold text-emerald-700 truncate">
                            {v.evidence.authorized_entity}
                          </p>
                        </div>
                      )}

                      {v.evidence.supplier_class && (
                        <div>
                          <span className="text-[9px] font-bold uppercase text-slate-400">MII Supplier Class</span>
                          <p className="font-bold text-indigo-700">
                            {v.evidence.supplier_class} ({v.evidence.verified_percentage ?? v.evidence.claimed_percentage}%)
                          </p>
                        </div>
                      )}

                      {v.evidence.standard_number && (
                        <div>
                          <span className="text-[9px] font-bold uppercase text-slate-400">BIS Standard</span>
                          <p className="font-bold text-slate-800">
                            {v.evidence.standard_number}
                          </p>
                        </div>
                      )}

                      {v.evidence.is_internal_check && (
                        <div>
                          <span className="text-[9px] font-bold uppercase text-slate-400">Verification Method</span>
                          <p className="font-bold text-slate-700">
                            Internal Evidence ({v.evidence.score})
                          </p>
                        </div>
                      )}

                      {v.evidence.authority && (
                        <div>
                          <span className="text-[9px] font-bold uppercase text-slate-400">Issuing Authority</span>
                          <p className="font-bold text-slate-800 truncate">
                            {v.evidence.authority}
                          </p>
                        </div>
                      )}

                      {v.evidence.total_checks !== undefined && (
                        <div>
                          <span className="text-[9px] font-bold uppercase text-slate-400">Cross-Document Matrix</span>
                          <p className="font-bold text-indigo-700">
                            {v.evidence.matched_checks}/{v.evidence.total_checks} Aligned
                          </p>
                        </div>
                      )}

                      {v.evidence.enterprise_classification && (
                        <div>
                          <span className="text-[9px] font-bold uppercase text-slate-400">MSME Classification</span>
                          <p className="font-bold text-indigo-700">
                            {v.evidence.enterprise_classification} ({v.evidence.major_activity || "Enterprise"})
                          </p>
                        </div>
                      )}

                      {v.evidence.company_type && (
                        <div>
                          <span className="text-[9px] font-bold uppercase text-slate-400">Company Type</span>
                          <p className="font-bold text-slate-800">
                            {v.evidence.company_type}
                          </p>
                        </div>
                      )}

                      {v.evidence.sector && (
                        <div>
                          <span className="text-[9px] font-bold uppercase text-slate-400">Startup Sector</span>
                          <p className="font-bold text-slate-800">
                            {v.evidence.sector}
                          </p>
                        </div>
                      )}

                      {v.evidence.valid_until && (
                        <div>
                          <span className="text-[9px] font-bold uppercase text-slate-400">Validity Window</span>
                          <p className="font-bold text-slate-800">
                            {v.evidence.valid_from ? `${v.evidence.valid_from} to ` : ""}{v.evidence.valid_until}
                          </p>
                        </div>
                      )}

                      {v.evidence.entity_type_description && (
                        <div>
                          <span className="text-[9px] font-bold uppercase text-slate-400">Taxpayer Entity Type</span>
                          <p className="font-bold text-slate-800">
                            {v.evidence.entity_type_description}
                          </p>
                        </div>
                      )}

                      {(v.evidence.registration_status || v.evidence.company_status || v.evidence.startup_status || v.evidence.authorization_status) && (
                        <div>
                          <span className="text-[9px] font-bold uppercase text-slate-400">Status</span>
                          <div>
                            <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                              (v.evidence.registration_status || v.evidence.company_status || v.evidence.startup_status || v.evidence.authorization_status) === "ACTIVE" ||
                              (v.evidence.registration_status || v.evidence.company_status || v.evidence.startup_status || v.evidence.authorization_status) === "VALID" ||
                              (v.evidence.registration_status || v.evidence.company_status || v.evidence.startup_status || v.evidence.authorization_status) === "RECOGNIZED"
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-amber-100 text-amber-800"
                            }`}>
                              {v.evidence.registration_status || v.evidence.company_status || v.evidence.startup_status || v.evidence.authorization_status}
                            </span>
                          </div>
                        </div>
                      )}

                      {v.evidence.reason && (
                        <div className="sm:col-span-2">
                          <span className="text-[9px] font-bold uppercase text-slate-400">Verification Outcome</span>
                          <p className="text-[11px] text-slate-700 font-medium mt-0.5">
                            {v.evidence.reason}
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {v.error_message && (
                    <div className="text-[11px] text-rose-700 bg-rose-50 p-2.5 rounded-lg border border-rose-200">
                      <strong>Notice:</strong> {v.error_message}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="py-12 text-center text-xs text-slate-500 space-y-2">
              <p>No statutory claims verified for this proposal yet.</p>
              <p className="text-[11px] text-slate-400">
                Upload and process statutory documents (GST certificate, PAN card, Udyam registration) in the Bid Workspace to trigger claim validation.
              </p>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
