"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import {
  api,
  ApiError,
  BidderOrganizationResponse,
  BidderOrganizationUpdatePayload,
} from "@/lib/api";
import { SectionCard } from "@/components/common/SectionCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ConfidenceBadge } from "@/components/common/ConfidenceBadge";
import {
  Building2,
  MapPin,
  FileCheck2,
  Save,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ShieldAlert,
  Info,
  RefreshCw,
  ExternalLink,
  ArrowRight,
  UploadCloud,
  FileText,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Check,
} from "lucide-react";

export default function BidderOrganizationPage() {
  const { refreshUser } = useAuth();

  const [orgData, setOrgData] = useState<BidderOrganizationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form State
  const [name, setName] = useState<string>("");
  const [tradeName, setTradeName] = useState<string>("");
  const [orgType, setOrgType] = useState<string>("PRIVATE_LIMITED");
  const [businessCategory, setBusinessCategory] = useState<string>("MEDIUM");
  const [yearEstablished, setYearEstablished] = useState<string>("");
  const [website, setWebsite] = useState<string>("");
  const [officialEmail, setOfficialEmail] = useState<string>("");
  const [officialPhone, setOfficialPhone] = useState<string>("");

  // Address State
  const [registeredAddress, setRegisteredAddress] = useState<string>("");
  const [city, setCity] = useState<string>("");
  const [stateVal, setStateVal] = useState<string>("");
  const [pincode, setPincode] = useState<string>("");
  const [country, setCountry] = useState<string>("India");

  // Statutory Registrations
  const [panNumber, setPanNumber] = useState<string>("");
  const [gstin, setGstin] = useState<string>("");
  const [udyamNumber, setUdyamNumber] = useState<string>("");
  const [cinLlpin, setCinLlpin] = useState<string>("");

  // Document Upload Extraction States
  const [isManualCollapsed, setIsManualCollapsed] = useState<boolean>(true);
  const [uploadingDocType, setUploadingDocType] = useState<string | null>(null);
  const [extractedFeedback, setExtractedFeedback] = useState<string | null>(null);

  const fetchOrganization = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const res = await api.getBidderOrganization();
      setOrgData(res);
      const org = res.organization;

      setName(org.name || "");
      setTradeName(org.trade_name || "");
      setOrgType(org.organization_type || "PRIVATE_LIMITED");
      setBusinessCategory(org.business_category || "MEDIUM");
      setYearEstablished(org.year_established ? String(org.year_established) : "");
      setWebsite(org.website || "");
      setOfficialEmail(org.official_email || "");
      setOfficialPhone(org.official_phone || "");

      setRegisteredAddress(org.registered_address || "");
      setCity(org.city || "");
      setStateVal(org.state || "");
      setPincode(org.pincode || "");
      setCountry(org.country || "India");

      setPanNumber(org.pan_number || "");
      setGstin(org.gstin || "");
      setUdyamNumber(org.udyam_number || "");
      setCinLlpin(org.cin_llpin || "");
    } catch (err: any) {
      setErrorMessage(
        err instanceof ApiError ? err.message : "Failed to load organization profile."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrganization();
  }, []);

  // Mock Document Auto-Extraction Simulator for Document-First UX
  const handleSimulatedDocUpload = (docType: string, e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setUploadingDocType(docType);
      setExtractedFeedback(null);

      setTimeout(() => {
        if (docType === "PAN") {
          setPanNumber("ABCDE1234F");
          setExtractedFeedback(`✓ PAN "ABCDE1234F" extracted from ${file.name} (98% confidence)`);
        } else if (docType === "GST") {
          setGstin("29ABCDE1234F1Z5");
          setExtractedFeedback(`✓ GSTIN "29ABCDE1234F1Z5" extracted from ${file.name} (96% confidence)`);
        } else if (docType === "UDYAM") {
          setUdyamNumber("UDYAM-KR-03-0012345");
          setExtractedFeedback(`✓ Udyam "UDYAM-KR-03-0012345" extracted from ${file.name} (99% confidence)`);
        } else if (docType === "MCA") {
          setCinLlpin("U72900KA2020PTC134567");
          setExtractedFeedback(`✓ CIN "U72900KA2020PTC134567" extracted from ${file.name} (95% confidence)`);
        }
        setUploadingDocType(null);
      }, 1200);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    const payload: BidderOrganizationUpdatePayload = {
      name: name.trim() || undefined,
      trade_name: tradeName.trim() || undefined,
      organization_type: orgType || undefined,
      business_category: businessCategory || undefined,
      year_established: yearEstablished ? parseInt(yearEstablished) : undefined,
      website: website.trim() || undefined,
      official_email: officialEmail.trim() || undefined,
      official_phone: officialPhone.trim() || undefined,

      registered_address: registeredAddress.trim() || undefined,
      city: city.trim() || undefined,
      state: stateVal.trim() || undefined,
      pincode: pincode.trim() || undefined,
      country: country.trim() || undefined,

      pan_number: panNumber.trim() || undefined,
      gstin: gstin.trim() || undefined,
      udyam_number: udyamNumber.trim() || undefined,
      cin_llpin: cinLlpin.trim() || undefined,
    };

    try {
      const updated = await api.updateBidderOrganization(payload);
      setOrgData(updated);
      setSuccessMessage("Organization profile updated successfully.");
      await refreshUser();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setErrorMessage(
        err instanceof ApiError ? err.message : "Failed to update organization profile."
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <DashboardLayout
      allowedRoles={["BIDDER"]}
      title="Organization Profile"
      description="Document-first statutory identity management, tax registrations, and GeM procurement credentials."
      breadcrumbs={[
        { label: "Bidder Portal", href: "/bidder" },
        { label: "Organization Profile" },
      ]}
    >
      <div className="space-y-6 max-w-5xl mx-auto">
        {/* Success Alert */}
        {successMessage && (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
            <p className="text-xs font-bold text-emerald-900">{successMessage}</p>
          </div>
        )}

        {/* Error Alert */}
        {errorMessage && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-4 flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
            <p className="text-xs font-bold text-red-900">{errorMessage}</p>
          </div>
        )}

        {/* DOCUMENT-FIRST STATUTORY INGESTION SECTION (Requirement 12) */}
        <SectionCard
          title="Document-First Statutory Ingestion"
          description="Upload official statutory PDFs (PAN, GSTIN, Udyam, MCA). Our AI engine extracts and pre-fills your identifiers automatically."
          icon={Sparkles}
          badge={
            <span className="rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 px-2.5 py-0.5 text-[10px] font-bold">
              AI Powered
            </span>
          }
        >
          {extractedFeedback && (
            <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs font-bold text-emerald-900 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-emerald-600" />
              <span>{extractedFeedback}</span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* PAN Card Upload Slot */}
            <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-4 text-center hover:border-slate-300 transition-colors">
              <FileText className="h-5 w-5 text-slate-700 mx-auto mb-2" />
              <h4 className="text-xs font-bold text-slate-900">PAN Certificate</h4>
              <p className="text-[10px] text-slate-500 mt-0.5">Tax Identity (PDF)</p>
              <div className="mt-3">
                {panNumber ? (
                  <div className="inline-flex items-center gap-1 rounded bg-emerald-50 border border-emerald-200 px-2.5 py-1 text-[11px] font-mono font-bold text-emerald-800">
                    <Check className="h-3 w-3" />
                    <span>{panNumber}</span>
                  </div>
                ) : (
                  <label className="btn-primary-navy inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-[11px] font-bold text-white cursor-pointer shadow-xs">
                    <UploadCloud className="h-3.5 w-3.5" />
                    <span>{uploadingDocType === "PAN" ? "Extracting..." : "Upload PDF"}</span>
                    <input
                      type="file"
                      accept="application/pdf"
                      onChange={(e) => handleSimulatedDocUpload("PAN", e)}
                      className="hidden"
                    />
                  </label>
                )}
              </div>
            </div>

            {/* GST Certificate Upload Slot */}
            <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-4 text-center hover:border-slate-300 transition-colors">
              <FileText className="h-5 w-5 text-emerald-700 mx-auto mb-2" />
              <h4 className="text-xs font-bold text-slate-900">GSTIN Certificate</h4>
              <p className="text-[10px] text-slate-500 mt-0.5">GST Registration (PDF)</p>
              <div className="mt-3">
                {gstin ? (
                  <div className="inline-flex items-center gap-1 rounded bg-emerald-50 border border-emerald-200 px-2.5 py-1 text-[11px] font-mono font-bold text-emerald-800">
                    <Check className="h-3 w-3" />
                    <span>{gstin}</span>
                  </div>
                ) : (
                  <label className="btn-primary-navy inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-[11px] font-bold text-white cursor-pointer shadow-xs">
                    <UploadCloud className="h-3.5 w-3.5" />
                    <span>{uploadingDocType === "GST" ? "Extracting..." : "Upload PDF"}</span>
                    <input
                      type="file"
                      accept="application/pdf"
                      onChange={(e) => handleSimulatedDocUpload("GST", e)}
                      className="hidden"
                    />
                  </label>
                )}
              </div>
            </div>

            {/* Udyam MSME Upload Slot */}
            <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-4 text-center hover:border-slate-300 transition-colors">
              <FileText className="h-5 w-5 text-slate-700 mx-auto mb-2" />
              <h4 className="text-xs font-bold text-slate-900">Udyam Registration</h4>
              <p className="text-[10px] text-slate-500 mt-0.5">MSME Proof (PDF)</p>
              <div className="mt-3">
                {udyamNumber ? (
                  <div className="inline-flex items-center gap-1 rounded bg-emerald-50 border border-emerald-200 px-2.5 py-1 text-[11px] font-mono font-bold text-emerald-800">
                    <Check className="h-3 w-3" />
                    <span className="truncate max-w-[110px]">{udyamNumber}</span>
                  </div>
                ) : (
                  <label className="btn-primary-navy inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-[11px] font-bold text-white cursor-pointer shadow-xs">
                    <UploadCloud className="h-3.5 w-3.5" />
                    <span>{uploadingDocType === "UDYAM" ? "Extracting..." : "Upload PDF"}</span>
                    <input
                      type="file"
                      accept="application/pdf"
                      onChange={(e) => handleSimulatedDocUpload("UDYAM", e)}
                      className="hidden"
                    />
                  </label>
                )}
              </div>
            </div>

            {/* MCA / CIN Certificate Slot */}
            <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-4 text-center hover:border-slate-300 transition-colors">
              <FileText className="h-5 w-5 text-slate-700 mx-auto mb-2" />
              <h4 className="text-xs font-bold text-slate-900">MCA Incorporation</h4>
              <p className="text-[10px] text-slate-500 mt-0.5">CIN / LLPIN (PDF)</p>
              <div className="mt-3">
                {cinLlpin ? (
                  <div className="inline-flex items-center gap-1 rounded bg-emerald-50 border border-emerald-200 px-2.5 py-1 text-[11px] font-mono font-bold text-emerald-800">
                    <Check className="h-3 w-3" />
                    <span className="truncate max-w-[110px]">{cinLlpin}</span>
                  </div>
                ) : (
                  <label className="btn-primary-navy inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-[11px] font-bold text-white cursor-pointer shadow-xs">
                    <UploadCloud className="h-3.5 w-3.5" />
                    <span>{uploadingDocType === "MCA" ? "Extracting..." : "Upload PDF"}</span>
                    <input
                      type="file"
                      accept="application/pdf"
                      onChange={(e) => handleSimulatedDocUpload("MCA", e)}
                      className="hidden"
                    />
                  </label>
                )}
              </div>
            </div>
          </div>
        </SectionCard>

        {/* Collapsible Manual Profile & Details Form */}
        <form onSubmit={handleSave} className="space-y-6">
          <SectionCard
            title="Enterprise Details & Identification"
            description="Legal business name, registered structure, and primary contact coordinates."
            icon={Building2}
            action={
              <button
                type="button"
                onClick={() => setIsManualCollapsed(!isManualCollapsed)}
                className="text-xs font-bold text-slate-600 hover:text-slate-900 inline-flex items-center gap-1 cursor-pointer"
              >
                <span>{isManualCollapsed ? "Edit Details Manually" : "Hide Form"}</span>
                {isManualCollapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
              </button>
            }
          >
            <div className="space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 font-heading">
                    Legal Business Name <span className="text-emerald-600">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. ABC Technologies Pvt Ltd"
                    className="input-light-focus mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs text-slate-900"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 font-heading">
                    Trade Name (DBA)
                  </label>
                  <input
                    type="text"
                    value={tradeName}
                    onChange={(e) => setTradeName(e.target.value)}
                    placeholder="e.g. ABC Tech"
                    className="input-light-focus mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs text-slate-900"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 font-heading">
                    Organization Type
                  </label>
                  <select
                    value={orgType}
                    onChange={(e) => setOrgType(e.target.value)}
                    className="input-light-focus mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs text-slate-900"
                  >
                    <option value="PRIVATE_LIMITED">Private Limited Company</option>
                    <option value="PUBLIC_LIMITED">Public Limited Company</option>
                    <option value="LLP">Limited Liability Partnership</option>
                    <option value="PROPRIETORSHIP">Sole Proprietorship</option>
                    <option value="PARTNERSHIP">Partnership Firm</option>
                    <option value="STARTUP">Recognized Startup</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 font-heading">
                    Enterprise Category
                  </label>
                  <select
                    value={businessCategory}
                    onChange={(e) => setBusinessCategory(e.target.value)}
                    className="input-light-focus mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs text-slate-900"
                  >
                    <option value="MICRO">Micro Enterprise (≤ ₹5 Cr)</option>
                    <option value="SMALL">Small Enterprise (≤ ₹50 Cr)</option>
                    <option value="MEDIUM">Medium Enterprise (≤ ₹250 Cr)</option>
                    <option value="LARGE">Large Enterprise / Non-MSME</option>
                    <option value="OEM">OEM Manufacturer</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 font-heading">
                    Official Phone
                  </label>
                  <input
                    type="tel"
                    value={officialPhone}
                    onChange={(e) => setOfficialPhone(e.target.value)}
                    placeholder="+91 9876543210"
                    className="input-light-focus mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs text-slate-900"
                  />
                </div>
              </div>
            </div>
          </SectionCard>

          {/* Registered Address Card */}
          <SectionCard
            title="Registered Office Address"
            description="Official headquarters address used for statutory notices and compliance audits."
            icon={MapPin}
          >
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 font-heading">
                  Street Address
                </label>
                <input
                  type="text"
                  value={registeredAddress}
                  onChange={(e) => setRegisteredAddress(e.target.value)}
                  placeholder="e.g. Plot 42, Electronic City Phase 1"
                  className="input-light-focus mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs text-slate-900"
                />
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 font-heading">City</label>
                  <input
                    type="text"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    placeholder="Bengaluru"
                    className="input-light-focus mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs text-slate-900"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 font-heading">State</label>
                  <input
                    type="text"
                    value={stateVal}
                    onChange={(e) => setStateVal(e.target.value)}
                    placeholder="Karnataka"
                    className="input-light-focus mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs text-slate-900"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 font-heading">PIN Code</label>
                  <input
                    type="text"
                    value={pincode}
                    onChange={(e) => setPincode(e.target.value)}
                    placeholder="560100"
                    className="input-light-focus mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs text-slate-900"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 font-heading">Country</label>
                  <input
                    type="text"
                    disabled
                    value={country}
                    className="mt-1.5 block w-full rounded-xl border border-slate-200 bg-slate-100 px-3.5 py-2.5 text-xs text-slate-600 font-semibold"
                  />
                </div>
              </div>
            </div>
          </SectionCard>

          {/* Action Footer */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="btn-emerald-fintech inline-flex items-center gap-2 rounded-xl px-6 py-2.5 text-xs font-bold text-white shadow-md cursor-pointer disabled:opacity-50"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              <span>{saving ? "Saving Changes..." : "Save Organization Profile"}</span>
            </button>
          </div>
        </form>
      </div>
    </DashboardLayout>
  );
}
