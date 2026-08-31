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
} from "lucide-react";

const ORGANIZATION_TYPES = [
  { value: "PROPRIETORSHIP", label: "Sole Proprietorship" },
  { value: "PARTNERSHIP", label: "Partnership Firm" },
  { value: "LLP", label: "Limited Liability Partnership (LLP)" },
  { value: "PRIVATE_LIMITED", label: "Private Limited Company (Pvt Ltd)" },
  { value: "PUBLIC_LIMITED", label: "Public Limited Company (Ltd)" },
  { value: "GOVERNMENT_ENTITY", label: "Government Entity / PSU / CPSE" },
  { value: "STARTUP", label: "Recognized Startup Entity" },
  { value: "OTHER", label: "Other Business Entity" },
];

const BUSINESS_CATEGORIES = [
  { value: "MICRO", label: "Micro Enterprise (Investment ≤ ₹1 Cr & Turnover ≤ ₹5 Cr)" },
  { value: "SMALL", label: "Small Enterprise (Investment ≤ ₹10 Cr & Turnover ≤ ₹50 Cr)" },
  { value: "MEDIUM", label: "Medium Enterprise (Investment ≤ ₹50 Cr & Turnover ≤ ₹250 Cr)" },
  { value: "LARGE", label: "Large Enterprise / Non-MSME" },
  { value: "OEM", label: "Original Equipment Manufacturer (OEM)" },
  { value: "TRADER", label: "Authorized Reseller / Trader" },
  { value: "SERVICE_PROVIDER", label: "Service Provider / Consultancy" },
  { value: "OTHER", label: "General Enterprise" },
];

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
  const [startupIndiaNumber, setStartupIndiaNumber] = useState<string>("");
  const [nsicNumber, setNsicNumber] = useState<string>("");
  const [epfoCode, setEpfoCode] = useState<string>("");
  const [esicCode, setEsicCode] = useState<string>("");

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
      setStartupIndiaNumber(org.startup_india_number || "");
      setNsicNumber(org.nsic_number || "");
      setEpfoCode(org.epfo_code || "");
      setEsicCode(org.esic_code || "");
    } catch (err: any) {
      setErrorMessage(
        err instanceof ApiError ? err.message : "Failed to load organization details."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrganization();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      setErrorMessage("Legal Business Name is required.");
      return;
    }

    setSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    const payload: BidderOrganizationUpdatePayload = {
      name: name.trim(),
      trade_name: tradeName.trim() || undefined,
      organization_type: orgType.trim() || undefined,
      business_category: businessCategory.trim() || undefined,
      year_established: yearEstablished ? parseInt(yearEstablished, 10) : undefined,
      website: website.trim() || undefined,
      official_email: officialEmail.trim() || undefined,
      official_phone: officialPhone.trim() || undefined,

      registered_address: registeredAddress.trim() || undefined,
      city: city.trim() || undefined,
      state: stateVal.trim() || undefined,
      pincode: pincode.trim() || undefined,
      country: country.trim() || "India",

      pan_number: panNumber.trim().toUpperCase() || undefined,
      gstin: gstin.trim().toUpperCase() || undefined,
      udyam_number: udyamNumber.trim().toUpperCase() || undefined,
      cin_llpin: cinLlpin.trim().toUpperCase() || undefined,
      startup_india_number: startupIndiaNumber.trim() || undefined,
      nsic_number: nsicNumber.trim() || undefined,
      epfo_code: epfoCode.trim() || undefined,
      esic_code: esicCode.trim() || undefined,
    };

    try {
      const res = await api.updateBidderOrganization(payload);
      setOrgData(res);
      setSuccessMessage("Organization profile and statutory details saved successfully.");
      await refreshUser();
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err: any) {
      setErrorMessage(
        err instanceof ApiError ? err.message : "Failed to save organization changes."
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <DashboardLayout
      allowedRoles={["BIDDER"]}
      title="My Organization"
      description="Manage statutory credentials, registered address, PAN, GSTIN, and MSME/Udyam registrations."
      breadcrumbs={[
        { label: "Bidder Portal", href: "/bidder" },
        { label: "My Organization" },
      ]}
    >
      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-xs">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-blue-700" />
          <p className="mt-3 text-sm font-medium text-slate-600">
            Loading organization data...
          </p>
        </div>
      ) : errorMessage && !orgData ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-center shadow-xs">
          <AlertCircle className="mx-auto h-8 w-8 text-rose-600" />
          <h3 className="mt-2 text-sm font-bold text-rose-900">
            Unable to Load Organization Details
          </h3>
          <p className="mt-1 text-xs text-rose-700">{errorMessage}</p>
          <button
            onClick={fetchOrganization}
            className="mt-4 inline-flex items-center gap-1.5 rounded-md bg-rose-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-rose-700 transition-colors shadow-xs"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Main Content Column (2/3 width) */}
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

            <form onSubmit={handleSave} className="space-y-6">
              {/* SECTION 1: Legal & Business Identity */}
              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
                <div className="flex items-center gap-2.5 border-b border-slate-100 pb-4 mb-5">
                  <div className="rounded-lg bg-blue-50 p-2 text-blue-700">
                    <Building2 className="h-5 w-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-slate-900">
                      Organization Information
                    </h2>
                    <p className="text-xs text-slate-500">
                      Official legal name and entity classification for GeM procurement.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {/* Legal Business Name */}
                  <div className="sm:col-span-2">
                    <label
                      htmlFor="legalName"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      Legal Business Name <span className="text-rose-500">*</span>
                    </label>
                    <input
                      id="legalName"
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      placeholder="e.g. Bharat Infotech Solutions Private Limited"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                    <p className="text-[11px] text-slate-500 mt-1">
                      Must match the name registered on your PAN and GSTIN certificates.
                    </p>
                  </div>

                  {/* Trade Name */}
                  <div>
                    <label
                      htmlFor="tradeName"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      Trade / Display Name
                    </label>
                    <input
                      id="tradeName"
                      type="text"
                      value={tradeName}
                      onChange={(e) => setTradeName(e.target.value)}
                      placeholder="e.g. Bharat Tech"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                  </div>

                  {/* Organization Type */}
                  <div>
                    <label
                      htmlFor="orgType"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      Organization Type <span className="text-rose-500">*</span>
                    </label>
                    <select
                      id="orgType"
                      value={orgType}
                      onChange={(e) => setOrgType(e.target.value)}
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    >
                      {ORGANIZATION_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Business Category */}
                  <div>
                    <label
                      htmlFor="businessCategory"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      Business MSME Category
                    </label>
                    <select
                      id="businessCategory"
                      value={businessCategory}
                      onChange={(e) => setBusinessCategory(e.target.value)}
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    >
                      {BUSINESS_CATEGORIES.map((c) => (
                        <option key={c.value} value={c.value}>
                          {c.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Year Established */}
                  <div>
                    <label
                      htmlFor="yearEstablished"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      Year Established
                    </label>
                    <input
                      id="yearEstablished"
                      type="number"
                      min="1800"
                      max={new Date().getFullYear()}
                      value={yearEstablished}
                      onChange={(e) => setYearEstablished(e.target.value)}
                      placeholder="e.g. 2015"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                  </div>

                  {/* Official Website */}
                  <div>
                    <label
                      htmlFor="website"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      Website URL
                    </label>
                    <input
                      id="website"
                      type="url"
                      value={website}
                      onChange={(e) => setWebsite(e.target.value)}
                      placeholder="https://www.example.com"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                  </div>

                  {/* Official Phone */}
                  <div>
                    <label
                      htmlFor="officialPhone"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      Official Corporate Phone
                    </label>
                    <input
                      id="officialPhone"
                      type="tel"
                      value={officialPhone}
                      onChange={(e) => setOfficialPhone(e.target.value)}
                      placeholder="e.g. +91 11 2345 6789"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                  </div>
                </div>
              </div>

              {/* SECTION 2: Registered Address */}
              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
                <div className="flex items-center gap-2.5 border-b border-slate-100 pb-4 mb-5">
                  <div className="rounded-lg bg-emerald-50 p-2 text-emerald-700">
                    <MapPin className="h-5 w-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-slate-900">
                      Registered Business Address
                    </h2>
                    <p className="text-xs text-slate-500">
                      Official statutory address for tender eligibility & state-level reservations.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {/* Address Line */}
                  <div className="sm:col-span-2">
                    <label
                      htmlFor="registeredAddress"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      Registered Address Line <span className="text-rose-500">*</span>
                    </label>
                    <input
                      id="registeredAddress"
                      type="text"
                      value={registeredAddress}
                      onChange={(e) => setRegisteredAddress(e.target.value)}
                      placeholder="e.g. Plot No. 102, Cyber City Tech Park, Phase 2"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                  </div>

                  {/* City */}
                  <div>
                    <label
                      htmlFor="city"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      City / District <span className="text-rose-500">*</span>
                    </label>
                    <input
                      id="city"
                      type="text"
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                      placeholder="e.g. New Delhi"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                  </div>

                  {/* State */}
                  <div>
                    <label
                      htmlFor="stateVal"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      State / Union Territory <span className="text-rose-500">*</span>
                    </label>
                    <input
                      id="stateVal"
                      type="text"
                      value={stateVal}
                      onChange={(e) => setStateVal(e.target.value)}
                      placeholder="e.g. Delhi"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                  </div>

                  {/* PIN Code */}
                  <div>
                    <label
                      htmlFor="pincode"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      Postal PIN Code <span className="text-rose-500">*</span>
                    </label>
                    <input
                      id="pincode"
                      type="text"
                      maxLength={6}
                      value={pincode}
                      onChange={(e) => setPincode(e.target.value)}
                      placeholder="e.g. 110001"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-mono text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                  </div>

                  {/* Country */}
                  <div>
                    <label
                      htmlFor="country"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      Country
                    </label>
                    <input
                      id="country"
                      type="text"
                      value={country}
                      onChange={(e) => setCountry(e.target.value)}
                      placeholder="India"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                  </div>
                </div>
              </div>

              {/* SECTION 3: Statutory & Business Registrations */}
              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
                <div className="flex items-center gap-2.5 border-b border-slate-100 pb-4 mb-5">
                  <div className="rounded-lg bg-purple-50 p-2 text-purple-700">
                    <FileCheck2 className="h-5 w-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-slate-900">
                      Statutory Identifiers & Registrations
                    </h2>
                    <p className="text-xs text-slate-500">
                      Tax, MSME, Corporate, and Labour compliance identifiers.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {/* PAN Number */}
                  <div>
                    <label
                      htmlFor="panNumber"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      PAN Number <span className="text-rose-500">*</span>
                    </label>
                    <input
                      id="panNumber"
                      type="text"
                      maxLength={10}
                      value={panNumber}
                      onChange={(e) => setPanNumber(e.target.value.toUpperCase())}
                      placeholder="e.g. ABCDE1234F"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-mono uppercase text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                    <p className="text-[11px] text-slate-500 mt-1">
                      10-character Permanent Account Number of entity.
                    </p>
                  </div>

                  {/* GSTIN */}
                  <div>
                    <label
                      htmlFor="gstin"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      GSTIN (GST Identification Number)
                    </label>
                    <input
                      id="gstin"
                      type="text"
                      maxLength={15}
                      value={gstin}
                      onChange={(e) => setGstin(e.target.value.toUpperCase())}
                      placeholder="e.g. 07ABCDE1234F1Z5"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-mono uppercase text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                    <p className="text-[11px] text-slate-500 mt-1">
                      15-character GSTIN registered in state of operation.
                    </p>
                  </div>

                  {/* Udyam Registration */}
                  <div>
                    <label
                      htmlFor="udyamNumber"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      Udyam Registration (MSME)
                    </label>
                    <input
                      id="udyamNumber"
                      type="text"
                      value={udyamNumber}
                      onChange={(e) => setUdyamNumber(e.target.value.toUpperCase())}
                      placeholder="UDYAM-XX-00-0000000"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-mono uppercase text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                    <p className="text-[11px] text-slate-500 mt-1">
                      Required for MSME purchase preference & EMD exemptions.
                    </p>
                  </div>

                  {/* CIN / LLPIN */}
                  <div>
                    <label
                      htmlFor="cinLlpin"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      CIN / LLPIN (MCA Registration)
                    </label>
                    <input
                      id="cinLlpin"
                      type="text"
                      value={cinLlpin}
                      onChange={(e) => setCinLlpin(e.target.value.toUpperCase())}
                      placeholder="e.g. U72200DL2018PTC123456"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-mono uppercase text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                    <p className="text-[11px] text-slate-500 mt-1">
                      Corporate / LLP identity for companies registered with MCA.
                    </p>
                  </div>

                  {/* Startup India Recognition */}
                  <div>
                    <label
                      htmlFor="startupIndiaNumber"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      Startup India (DPIIT) Number
                    </label>
                    <input
                      id="startupIndiaNumber"
                      type="text"
                      value={startupIndiaNumber}
                      onChange={(e) => setStartupIndiaNumber(e.target.value)}
                      placeholder="e.g. DIPP12345"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                  </div>

                  {/* NSIC Registration */}
                  <div>
                    <label
                      htmlFor="nsicNumber"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      NSIC Registration Number
                    </label>
                    <input
                      id="nsicNumber"
                      type="text"
                      value={nsicNumber}
                      onChange={(e) => setNsicNumber(e.target.value)}
                      placeholder="e.g. NSIC/DEL/2022/001"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                  </div>

                  {/* EPFO Code */}
                  <div>
                    <label
                      htmlFor="epfoCode"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      EPFO Establishment Code
                    </label>
                    <input
                      id="epfoCode"
                      type="text"
                      value={epfoCode}
                      onChange={(e) => setEpfoCode(e.target.value)}
                      placeholder="e.g. DL/CPM/1234567/000"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                  </div>

                  {/* ESIC Code */}
                  <div>
                    <label
                      htmlFor="esicCode"
                      className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                    >
                      ESIC Employer Code
                    </label>
                    <input
                      id="esicCode"
                      type="text"
                      value={esicCode}
                      onChange={(e) => setEsicCode(e.target.value)}
                      placeholder="e.g. 11000123450001001"
                      className="block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-700 shadow-xs"
                    />
                  </div>
                </div>
              </div>

              {/* Form Submission Action */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center gap-2 rounded-md bg-blue-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50 transition-colors shadow-xs"
                >
                  {saving ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Saving Organization Details...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4" />
                      Save Changes
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Right Sidebar Column (1/3 width) */}
          <div className="space-y-6">
            {/* Real-time Profile Completion Card */}
            {orgData?.completion && (
              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Profile Readiness
                  </h3>
                  <span
                    className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold border ${
                      orgData.completion.is_complete
                        ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                        : "bg-amber-50 text-amber-800 border-amber-200"
                    }`}
                  >
                    {orgData.completion.is_complete ? "Complete" : "Incomplete"}
                  </span>
                </div>

                <div className="flex items-baseline justify-between mb-1.5">
                  <span className="text-3xl font-extrabold font-mono text-slate-900">
                    {orgData.completion.completion_percentage}%
                  </span>
                  <span className="text-xs text-slate-500">
                    {orgData.completion.completed_fields_count} of{" "}
                    {orgData.completion.total_required_fields} mandatory fields
                  </span>
                </div>

                {/* Progress bar */}
                <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100 mb-4">
                  <div
                    className={`h-full transition-all duration-500 ${
                      orgData.completion.is_complete
                        ? "bg-emerald-600"
                        : orgData.completion.completion_percentage >= 70
                        ? "bg-blue-600"
                        : "bg-amber-500"
                    }`}
                    style={{
                      width: `${orgData.completion.completion_percentage}%`,
                    }}
                  />
                </div>

                {orgData.completion.missing_required_fields.length > 0 ? (
                  <div className="rounded-lg bg-amber-50/70 border border-amber-200 p-3.5 text-xs text-amber-900">
                    <p className="font-semibold mb-1.5 flex items-center gap-1">
                      <AlertCircle className="h-3.5 w-3.5 text-amber-700" />
                      Pending Mandatory Items:
                    </p>
                    <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-800 font-medium">
                      {orgData.completion.missing_required_fields.map(
                        (field, idx) => (
                          <li key={idx}>{field}</li>
                        )
                      )}
                    </ul>
                    {orgData.completion.missing_required_fields.some(
                      (f) => f.includes("Contact") || f.includes("Signatory")
                    ) && (
                      <Link
                        href="/bidder/profile"
                        className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-blue-700 hover:text-blue-900"
                      >
                        Update in Contact Profile
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    )}
                  </div>
                ) : (
                  <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3.5 text-xs text-emerald-900">
                    <div className="flex items-center gap-1.5 font-bold text-emerald-800 mb-1">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      Profile 100% Complete
                    </div>
                    <p className="text-[11px] text-emerald-700">
                      Your business entity is eligible for procurement participation.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Verification Disclaimer Box */}
            <div className="rounded-xl border border-blue-200 bg-blue-50/60 p-5">
              <div className="flex items-start gap-3">
                <Info className="h-5 w-5 text-blue-800 shrink-0 mt-0.5" />
                <div className="text-xs text-slate-700 space-y-1.5">
                  <p className="font-bold text-blue-900">
                    Statutory Verification Notice
                  </p>
                  <p className="text-[11px] leading-relaxed text-slate-600">
                    Statutory identifiers entered in this profile are format-validated. Official automated verification against MCA, GSTN, and MSME Udyam registries will occur during the automated compliance verification stage.
                  </p>
                </div>
              </div>
            </div>

            {/* Procurement Participation Guidelines */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                GeM Procurement Readiness
              </h4>
              <p className="text-xs text-slate-600 leading-relaxed">
                Keeping your PAN, GSTIN, and MSME numbers up to date ensures seamless evaluation during GeM clause matching and statutory bid audits.
              </p>
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <span>Security Standard</span>
                <span className="font-mono font-semibold text-slate-700">ISO 27001 / GeM</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
