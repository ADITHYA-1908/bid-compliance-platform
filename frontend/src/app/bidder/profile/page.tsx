"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import {
  api,
  ApiError,
  BidderProfileResponse,
  BidderProfileUpdatePayload,
} from "@/lib/api";
import {
  User,
  Building2,
  Phone,
  Briefcase,
  Mail,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  AlertCircle,
  ArrowRight,
  Save,
  Loader2,
  RefreshCw,
} from "lucide-react";

export default function BidderProfilePage() {
  const { user, refreshUser } = useAuth();

  const [profileData, setProfileData] = useState<BidderProfileResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form State
  const [fullName, setFullName] = useState<string>("");
  const [phone, setPhone] = useState<string>("");
  const [designation, setDesignation] = useState<string>("");

  const fetchProfile = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await api.getBidderProfile();
      setProfileData(data);
      setFullName(data.profile.full_name || "");
      setPhone(data.profile.phone || "");
      setDesignation(data.profile.designation || "");
    } catch (err: any) {
      setErrorMessage(
        err instanceof ApiError ? err.message : "Failed to load bidder profile."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim()) {
      setErrorMessage("Full name is required.");
      return;
    }

    setSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    const payload: BidderProfileUpdatePayload = {
      full_name: fullName.trim(),
      phone: phone.trim() || undefined,
      designation: designation.trim() || undefined,
    };

    try {
      const updated = await api.updateBidderProfile(payload);
      setProfileData(updated);
      setSuccessMessage("Profile details updated successfully.");
      await refreshUser();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setErrorMessage(
        err instanceof ApiError
          ? err.message
          : "Failed to update profile. Please try again."
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <DashboardLayout
      allowedRoles={["BIDDER"]}
      title="My Profile"
      description="Manage your authorized signatory credentials and primary contact information."
      breadcrumbs={[
        { label: "Bidder Portal", href: "/bidder" },
        { label: "My Profile" },
      ]}
    >
      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-xs">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-blue-700" />
          <p className="mt-3 text-sm font-medium text-slate-600">
            Loading bidder profile...
          </p>
        </div>
      ) : errorMessage && !profileData ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-center shadow-xs">
          <AlertCircle className="mx-auto h-8 w-8 text-rose-600" />
          <h3 className="mt-2 text-sm font-bold text-rose-900">
            Unable to Load Profile
          </h3>
          <p className="mt-1 text-xs text-rose-700">{errorMessage}</p>
          <button
            onClick={fetchProfile}
            className="mt-4 inline-flex items-center gap-1.5 rounded-md bg-rose-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-rose-700 transition-colors shadow-xs"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Main Form Column (2/3 width on large screens) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Feedback Alerts */}
            {successMessage && (
              <div className="flex items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-emerald-800 text-sm">
                <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" />
                <p className="font-medium">{successMessage}</p>
              </div>
            )}

            {errorMessage && (
              <div className="flex items-center gap-3 rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-800 text-sm">
                <AlertCircle className="h-5 w-5 shrink-0 text-rose-600" />
                <p className="font-medium">{errorMessage}</p>
              </div>
            )}

            {/* Profile Edit Card */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-6">
                <div>
                  <h2 className="text-base font-bold text-slate-900">
                    Authorized Signatory & Contact Info
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    This contact identity is attached to statutory bid submissions.
                  </p>
                </div>
                <span className="inline-flex items-center rounded-md bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700 border border-blue-200">
                  {profileData?.profile.role || "BIDDER"}
                </span>
              </div>

              <form onSubmit={handleSave} className="space-y-4">
                {/* Full Name */}
                <div>
                  <label
                    htmlFor="fullName"
                    className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                  >
                    Full Name / Authorized Signatory{" "}
                    <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                      <User className="h-4 w-4 text-slate-400" />
                    </div>
                    <input
                      id="fullName"
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      required
                      placeholder="e.g. Rajesh Kumar Sharma"
                      className="block w-full rounded-md border border-slate-300 bg-white pl-9.5 pr-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                  </div>
                </div>

                {/* Email Address (Read-only account identifier) */}
                <div>
                  <label
                    htmlFor="email"
                    className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                  >
                    Registered Account Email (Immutable)
                  </label>
                  <div className="relative">
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                      <Mail className="h-4 w-4 text-slate-400" />
                    </div>
                    <input
                      id="email"
                      type="email"
                      value={profileData?.profile.email || user?.email || ""}
                      disabled
                      className="block w-full rounded-md border border-slate-200 bg-slate-50 pl-9.5 pr-3 py-2 text-sm font-mono text-slate-600 cursor-not-allowed shadow-xs"
                    />
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Used for platform authentication and official GeM audit notices.
                  </p>
                </div>

                {/* Designation */}
                <div>
                  <label
                    htmlFor="designation"
                    className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                  >
                    Signatory Designation
                  </label>
                  <div className="relative">
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                      <Briefcase className="h-4 w-4 text-slate-400" />
                    </div>
                    <input
                      id="designation"
                      type="text"
                      value={designation}
                      onChange={(e) => setDesignation(e.target.value)}
                      placeholder="e.g. Managing Director, Partner, Proprietor"
                      className="block w-full rounded-md border border-slate-300 bg-white pl-9.5 pr-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                  </div>
                </div>

                {/* Contact Phone */}
                <div>
                  <label
                    htmlFor="phone"
                    className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                  >
                    Contact Mobile / Phone{" "}
                    <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                      <Phone className="h-4 w-4 text-slate-400" />
                    </div>
                    <input
                      id="phone"
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="e.g. +91 98765 43210"
                      className="block w-full rounded-md border border-slate-300 bg-white pl-9.5 pr-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Required for statutory notifications and OTP verifications.
                  </p>
                </div>

                {/* Save Button */}
                <div className="pt-4 flex items-center justify-end">
                  <button
                    type="submit"
                    disabled={saving}
                    className="inline-flex items-center gap-2 rounded-md bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50 transition-colors shadow-xs"
                  >
                    {saving ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Saving Changes...
                      </>
                    ) : (
                      <>
                        <Save className="h-4 w-4" />
                        Save Profile
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>

          {/* Right Sidebar Column (1/3 width) */}
          <div className="space-y-6">
            {/* Profile Completion Indicator */}
            {profileData?.completion && (
              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Profile Readiness
                  </h3>
                  <span
                    className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold border ${
                      profileData.completion.is_complete
                        ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                        : "bg-amber-50 text-amber-800 border-amber-200"
                    }`}
                  >
                    {profileData.completion.is_complete ? (
                      <>
                        <CheckCircle2 className="h-3 w-3 text-emerald-600 shrink-0" />
                        <span>Ready for Bidding</span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="h-3 w-3 text-amber-600 shrink-0" />
                        <span>Incomplete</span>
                      </>
                    )}
                  </span>
                </div>

                <div className="flex items-baseline justify-between mb-1.5">
                  <span className="text-3xl font-extrabold font-mono text-slate-900">
                    {profileData.completion.completion_percentage}%
                  </span>
                  <span className="text-xs text-slate-500">
                    {profileData.completion.completed_fields_count} of{" "}
                    {profileData.completion.total_required_fields} requirements
                  </span>
                </div>

                {/* Progress bar */}
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 mb-4">
                  <div
                    className={`h-full transition-all duration-500 ${
                      profileData.completion.is_complete
                        ? "bg-emerald-600"
                        : profileData.completion.completion_percentage > 50
                        ? "bg-blue-600"
                        : "bg-amber-500"
                    }`}
                    style={{
                      width: `${profileData.completion.completion_percentage}%`,
                    }}
                  />
                </div>

                {profileData.completion.missing_required_fields.length > 0 ? (
                  <div className="rounded-lg bg-amber-50/70 border border-amber-200 p-3.5 text-xs text-amber-900">
                    <p className="font-semibold mb-1.5 flex items-center gap-1">
                      <AlertTriangle className="h-3.5 w-3.5 text-amber-700 shrink-0" />
                      Pending Mandatory Items:
                    </p>
                    <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-800 font-medium">
                      {profileData.completion.missing_required_fields.map(
                        (field, idx) => (
                          <li key={idx}>{field}</li>
                        )
                      )}
                    </ul>
                    <Link
                      href="/bidder/organization"
                      className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-blue-700 hover:text-blue-900"
                    >
                      Complete in Organization Setup
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                ) : (
                  <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3 text-xs text-emerald-900 flex items-start gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                    <p>
                      All mandatory bidder identity and organization requirements
                      are satisfied.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Linked Organization Master Card */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
              <div className="flex items-center gap-2 mb-3">
                <div className="rounded-lg bg-blue-50 p-2 text-blue-700">
                  <Building2 className="h-4 w-4" />
                </div>
                <h3 className="text-sm font-bold text-slate-900">
                  Linked Entity
                </h3>
              </div>

              <div className="rounded-lg bg-slate-50 p-3.5 border border-slate-200/75 space-y-2 text-xs">
                <div>
                  <span className="text-slate-500 font-medium">
                    Legal Entity Name:
                  </span>
                  <p className="font-bold text-slate-900 mt-0.5 text-sm">
                    {profileData?.profile.organization?.name ||
                      user?.organization ||
                      "N/A"}
                  </p>
                </div>

                {profileData?.profile.organization?.trade_name && (
                  <div>
                    <span className="text-slate-500 font-medium">Trade Name:</span>
                    <p className="font-semibold text-slate-700 mt-0.5">
                      {profileData.profile.organization.trade_name}
                    </p>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-200">
                  <div>
                    <span className="text-slate-500 font-medium">PAN:</span>
                    <p className="font-mono font-semibold text-slate-800">
                      {profileData?.profile.organization?.pan_number || "—"}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-500 font-medium">GSTIN:</span>
                    <p className="font-mono font-semibold text-slate-800">
                      {profileData?.profile.organization?.gstin || "—"}
                    </p>
                  </div>
                </div>
              </div>

              <Link
                href="/bidder/organization"
                className="mt-4 flex w-full items-center justify-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-xs"
              >
                Manage Organization & Registrations
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>

            {/* Compliance Trust Note */}
            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <div className="flex items-start gap-2.5">
                <ShieldCheck className="h-4 w-4 text-blue-700 shrink-0 mt-0.5" />
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  BidVerify AI enforces cryptographic linkage between authorized
                  signatory credentials and procurement tender submissions.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
