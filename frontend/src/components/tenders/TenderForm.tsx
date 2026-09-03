"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Tender,
  TenderCreatePayload,
  TenderUpdatePayload,
} from "@/lib/api";
import { toDatetimeLocalString } from "@/lib/formatters";
import { ArrowLeft, Save, ShieldAlert } from "lucide-react";

interface TenderFormProps {
  mode: "create" | "edit";
  initialData?: Tender | null;
  isSubmitting?: boolean;
  serverError?: string | null;
  onSubmit: (payload: TenderCreatePayload | TenderUpdatePayload) => Promise<void>;
  cancelHref: string;
}

export function TenderForm({
  mode,
  initialData,
  isSubmitting = false,
  serverError = null,
  onSubmit,
  cancelHref,
}: TenderFormProps) {
  const [tenderNumber, setTenderNumber] = useState(initialData?.tender_number || "");
  const [title, setTitle] = useState(initialData?.title || "");
  const [description, setDescription] = useState(initialData?.description || "");
  const [department, setDepartment] = useState(initialData?.department || "");
  const [category, setCategory] = useState(initialData?.category || "");
  const [procurementType, setProcurementType] = useState(initialData?.procurement_type || "GOODS");
  const [estimatedValue, setEstimatedValue] = useState<string>(
    initialData?.estimated_value !== undefined && initialData?.estimated_value !== null
      ? String(initialData.estimated_value)
      : ""
  );
  const [currency, setCurrency] = useState(initialData?.currency || "INR");

  const [publishDate, setPublishDate] = useState(
    toDatetimeLocalString(initialData?.publish_date)
  );
  const [submissionStartDate, setSubmissionStartDate] = useState(
    toDatetimeLocalString(initialData?.submission_start_date)
  );
  const [submissionEndDate, setSubmissionEndDate] = useState(
    toDatetimeLocalString(initialData?.submission_end_date)
  );
  const [evaluationStartDate, setEvaluationStartDate] = useState(
    toDatetimeLocalString(initialData?.evaluation_start_date)
  );

  const [evaluationMethod, setEvaluationMethod] = useState<string>(
    initialData?.evaluation_method || "L1_LOWEST_COMPLIANT_BID"
  );
  const [technicalWeight, setTechnicalWeight] = useState<number>(
    initialData?.technical_weight !== undefined && initialData?.technical_weight !== null
      ? initialData.technical_weight
      : 70
  );
  const [financialWeight, setFinancialWeight] = useState<number>(
    initialData?.financial_weight !== undefined && initialData?.financial_weight !== null
      ? initialData.financial_weight
      : 30
  );

  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (initialData) {
      setTenderNumber(initialData.tender_number || "");
      setTitle(initialData.title || "");
      setDescription(initialData.description || "");
      setDepartment(initialData.department || "");
      setCategory(initialData.category || "");
      setProcurementType(initialData.procurement_type || "GOODS");
      setEstimatedValue(
        initialData.estimated_value !== undefined && initialData.estimated_value !== null
          ? String(initialData.estimated_value)
          : ""
      );
      setCurrency(initialData.currency || "INR");
      setEvaluationMethod(initialData.evaluation_method || "L1_LOWEST_COMPLIANT_BID");
      setTechnicalWeight(initialData.technical_weight !== undefined && initialData.technical_weight !== null ? initialData.technical_weight : 70);
      setFinancialWeight(initialData.financial_weight !== undefined && initialData.financial_weight !== null ? initialData.financial_weight : 30);
      setPublishDate(toDatetimeLocalString(initialData.publish_date));
      setSubmissionStartDate(toDatetimeLocalString(initialData.submission_start_date));
      setSubmissionEndDate(toDatetimeLocalString(initialData.submission_end_date));
      setEvaluationStartDate(toDatetimeLocalString(initialData.evaluation_start_date));
    }
  }, [initialData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    // Client-side validations
    if (mode === "create" && !tenderNumber.trim()) {
      setValidationError("Tender number is required (e.g. GEM/2026/B/001245).");
      return;
    }

    if (!title.trim()) {
      setValidationError("Tender title is required.");
      return;
    }

    if (estimatedValue && parseFloat(estimatedValue) < 0) {
      setValidationError("Estimated value cannot be negative.");
      return;
    }

    if (evaluationMethod === "QCBS_TECHNICAL_FINANCIAL" && technicalWeight + financialWeight !== 100) {
      setValidationError("For QCBS evaluation, Technical Weight + Financial Weight must equal exactly 100%.");
      return;
    }

    if (submissionStartDate && submissionEndDate) {
      if (new Date(submissionEndDate) < new Date(submissionStartDate)) {
        setValidationError("Submission end date cannot be earlier than submission start date.");
        return;
      }
    }

    if (publishDate && submissionStartDate) {
      if (new Date(submissionStartDate) < new Date(publishDate)) {
        setValidationError("Submission start date cannot be earlier than publish date.");
        return;
      }
    }

    if (submissionEndDate && evaluationStartDate) {
      if (new Date(evaluationStartDate) < new Date(submissionEndDate)) {
        setValidationError("Evaluation start date cannot be earlier than submission end date.");
        return;
      }
    }

    const payload: TenderCreatePayload | TenderUpdatePayload = {
      title: title.trim(),
      description: description.trim() || null,
      department: department.trim() || null,
      category: category.trim() || null,
      procurement_type: procurementType || "GOODS",
      estimated_value: estimatedValue ? parseFloat(estimatedValue) : null,
      currency: currency.trim() || "INR",
      evaluation_method: evaluationMethod,
      technical_weight: technicalWeight,
      financial_weight: financialWeight,
      publish_date: publishDate ? new Date(publishDate).toISOString() : null,
      submission_start_date: submissionStartDate ? new Date(submissionStartDate).toISOString() : null,
      submission_end_date: submissionEndDate ? new Date(submissionEndDate).toISOString() : null,
      evaluation_start_date: evaluationStartDate ? new Date(evaluationStartDate).toISOString() : null,
    };

    if (mode === "create") {
      (payload as TenderCreatePayload).tender_number = tenderNumber.trim();
    }

    await onSubmit(payload);
  };

  const displayError = validationError || serverError;

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {displayError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4" role="alert">
          <div className="flex items-start gap-3">
            <ShieldAlert className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
            <div>
              <h4 className="text-xs font-bold text-red-900">Validation / Submission Error</h4>
              <p className="text-xs text-red-700 mt-0.5">{displayError}</p>
            </div>
          </div>
        </div>
      )}

      {/* Section 1: Basic Information */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-5">
        <div className="border-b border-slate-100 pb-3">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            1. Basic Opportunity Information
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Identify the tender reference number and procurement objective.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor="tenderNumber" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              GeM Tender Number <span className="text-red-500">*</span>
            </label>
            <div className="mt-1.5">
              <input
                id="tenderNumber"
                type="text"
                required
                disabled={mode === "edit"}
                value={tenderNumber}
                onChange={(e) => setTenderNumber(e.target.value)}
                placeholder="e.g. GEM/2026/B/001245"
                className={`block w-full rounded-lg border px-3.5 py-2 text-xs font-mono text-slate-900 placeholder:text-slate-400 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600 ${
                  mode === "edit"
                    ? "bg-slate-100 text-slate-500 border-slate-200 cursor-not-allowed"
                    : "border-slate-300 bg-white"
                }`}
              />
            </div>
            <p className="mt-1 text-[11px] text-slate-500">
              {mode === "edit" ? "Tender number cannot be modified once drafted." : "Must be unique across the GeM procurement portal."}
            </p>
          </div>

          <div>
            <label htmlFor="title" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              Tender Title <span className="text-red-500">*</span>
            </label>
            <div className="mt-1.5">
              <input
                id="title"
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Supply of 500 Business Laptops"
                className="block w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
              />
            </div>
            <p className="mt-1 text-[11px] text-slate-500">
              Concise, descriptive title summarizing the goods or services.
            </p>
          </div>

          <div className="sm:col-span-2">
            <label htmlFor="description" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              Procurement Scope & Description
            </label>
            <div className="mt-1.5">
              <textarea
                id="description"
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Provide a comprehensive summary of the procurement objective, technical specifications, and key deliverables..."
                className="block w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Section 2: Procurement Details */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-5">
        <div className="border-b border-slate-100 pb-3">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            2. Departmental & Financial Details
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Configure financial valuation, procurement classification, and administrative division.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
          <div>
            <label htmlFor="department" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              Department / Ministry
            </label>
            <div className="mt-1.5">
              <input
                id="department"
                type="text"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                placeholder="e.g. Department of IT"
                className="block w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
              />
            </div>
          </div>

          <div>
            <label htmlFor="category" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              Product / Service Category
            </label>
            <div className="mt-1.5">
              <input
                id="category"
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="e.g. IT Equipment, Medical Supplies"
                className="block w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
              />
            </div>
          </div>

          <div>
            <label htmlFor="procurementType" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              Procurement Type
            </label>
            <div className="mt-1.5">
              <select
                id="procurementType"
                value={procurementType}
                onChange={(e) => setProcurementType(e.target.value)}
                className="block w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs text-slate-900 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
              >
                <option value="GOODS">Goods / Hardware</option>
                <option value="SERVICES">Services / Operations</option>
                <option value="WORKS">Works / Infrastructure</option>
              </select>
            </div>
          </div>

          <div className="sm:col-span-2">
            <label htmlFor="estimatedValue" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              Estimated Total Contract Value ({currency})
            </label>
            <div className="mt-1.5 relative">
              <input
                id="estimatedValue"
                type="number"
                step="0.01"
                min="0"
                value={estimatedValue}
                onChange={(e) => setEstimatedValue(e.target.value)}
                placeholder="e.g. 25000000"
                className="block w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-mono text-slate-900 placeholder:text-slate-400 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
              />
            </div>
            <p className="mt-1 text-[11px] text-slate-500">
              Expressed in numerical currency format (e.g. 2,50,00,000 INR = 2.5 Crore).
            </p>
          </div>

          <div>
            <label htmlFor="currency" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              Currency
            </label>
            <div className="mt-1.5">
              <input
                id="currency"
                type="text"
                value={currency}
                onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                maxLength={10}
                placeholder="INR"
                className="block w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-mono text-slate-900 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600 uppercase"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Section 3: Schedule & Deadlines */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-5">
        <div className="border-b border-slate-100 pb-3">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            3. Procurement Schedule & Timelines
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Key milestones for publication, bid acceptance, and technical evaluation.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor="publishDate" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              Publication Date
            </label>
            <div className="mt-1.5">
              <input
                id="publishDate"
                type="datetime-local"
                value={publishDate}
                onChange={(e) => setPublishDate(e.target.value)}
                className="block w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-mono text-slate-900 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
              />
            </div>
          </div>

          <div>
            <label htmlFor="submissionStartDate" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              Bid Submission Start Date
            </label>
            <div className="mt-1.5">
              <input
                id="submissionStartDate"
                type="datetime-local"
                value={submissionStartDate}
                onChange={(e) => setSubmissionStartDate(e.target.value)}
                className="block w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-mono text-slate-900 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
              />
            </div>
          </div>

          <div>
            <label htmlFor="submissionEndDate" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              Bid Submission Deadline (End Date)
            </label>
            <div className="mt-1.5">
              <input
                id="submissionEndDate"
                type="datetime-local"
                value={submissionEndDate}
                onChange={(e) => setSubmissionEndDate(e.target.value)}
                className="block w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-mono text-slate-900 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
              />
            </div>
          </div>

          <div>
            <label htmlFor="evaluationStartDate" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
              Evaluation & Verification Start Date
            </label>
            <div className="mt-1.5">
              <input
                id="evaluationStartDate"
                type="datetime-local"
                value={evaluationStartDate}
                onChange={(e) => setEvaluationStartDate(e.target.value)}
                className="block w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-mono text-slate-900 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Section 4: Commercial Evaluation Method & Weights */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-5">
        <div className="border-b border-slate-100 pb-3">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider font-heading">
            4. Commercial Evaluation Method & Scoring Weightage
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Configure how compliant bids will be ranked and commercially evaluated.
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Evaluation Methodology
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <label
                className={`flex flex-col p-4 rounded-xl border cursor-pointer transition-all ${
                  evaluationMethod === "L1_LOWEST_COMPLIANT_BID"
                    ? "border-navy-900 bg-slate-50 ring-2 ring-navy-900"
                    : "border-slate-200 bg-white hover:border-slate-300"
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-900 font-heading">Lowest Compliant Bid (L1)</span>
                  <input
                    type="radio"
                    name="evalMethod"
                    checked={evaluationMethod === "L1_LOWEST_COMPLIANT_BID"}
                    onChange={() => setEvaluationMethod("L1_LOWEST_COMPLIANT_BID")}
                    className="text-navy-900"
                  />
                </div>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Ranks purely on lowest quoted price among bidders passing mandatory eligibility.
                </p>
              </label>

              <label
                className={`flex flex-col p-4 rounded-xl border cursor-pointer transition-all ${
                  evaluationMethod === "QCBS_TECHNICAL_FINANCIAL"
                    ? "border-navy-900 bg-slate-50 ring-2 ring-navy-900"
                    : "border-slate-200 bg-white hover:border-slate-300"
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-900 font-heading">Technical + Financial (QCBS)</span>
                  <input
                    type="radio"
                    name="evalMethod"
                    checked={evaluationMethod === "QCBS_TECHNICAL_FINANCIAL"}
                    onChange={() => setEvaluationMethod("QCBS_TECHNICAL_FINANCIAL")}
                    className="text-navy-900"
                  />
                </div>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Quality and cost based selection. Technical score and financial score weighted to 100%.
                </p>
              </label>

              <label
                className={`flex flex-col p-4 rounded-xl border cursor-pointer transition-all ${
                  evaluationMethod === "CUSTOM_WEIGHTED"
                    ? "border-navy-900 bg-slate-50 ring-2 ring-navy-900"
                    : "border-slate-200 bg-white hover:border-slate-300"
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-900 font-heading">Custom Weighted</span>
                  <input
                    type="radio"
                    name="evalMethod"
                    checked={evaluationMethod === "CUSTOM_WEIGHTED"}
                    onChange={() => setEvaluationMethod("CUSTOM_WEIGHTED")}
                    className="text-navy-900"
                  />
                </div>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Custom weighted evaluation formula for multi-parameter complex tenders.
                </p>
              </label>
            </div>
          </div>

          {evaluationMethod === "QCBS_TECHNICAL_FINANCIAL" && (
            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-900 font-heading">QCBS Weight Allocation</span>
                <span
                  className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${
                    technicalWeight + financialWeight === 100
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-red-100 text-red-800"
                  }`}
                >
                  Total: {technicalWeight + financialWeight}% {technicalWeight + financialWeight === 100 ? "✓ Valid" : "(Must equal 100%)"}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700">
                    Technical Quality Weight (%)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="99"
                    value={technicalWeight}
                    onChange={(e) => {
                      const val = parseInt(e.target.value) || 0;
                      setTechnicalWeight(val);
                      setFinancialWeight(100 - val);
                    }}
                    className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-mono text-slate-900 focus:border-navy-900 focus:ring-1 focus:ring-navy-900"
                  />
                  <p className="text-[10px] text-slate-500 mt-1">Weight for technical compliance and capability evaluation.</p>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700">
                    Commercial Financial Weight (%)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="99"
                    value={financialWeight}
                    onChange={(e) => {
                      const val = parseInt(e.target.value) || 0;
                      setFinancialWeight(val);
                      setTechnicalWeight(100 - val);
                    }}
                    className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-mono text-slate-900 focus:border-navy-900 focus:ring-1 focus:ring-navy-900"
                  />
                  <p className="text-[10px] text-slate-500 mt-1">Financial score formula: (Lowest Price / Bidder Price) × 100.</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Form Action Controls */}
      <div className="flex items-center justify-end gap-3 pt-2">
        <Link
          href={cancelHref}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Cancel
        </Link>

        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex items-center gap-2 rounded-lg bg-purple-900 px-5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-purple-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-purple-900 disabled:opacity-50 transition-colors cursor-pointer"
        >
          {isSubmitting ? (
            <>
              <svg className="h-3.5 w-3.5 animate-spin text-white" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Saving Tender...
            </>
          ) : (
            <>
              <Save className="h-3.5 w-3.5" />
              {mode === "create" ? "Create Tender (Draft)" : "Save Changes"}
            </>
          )}
        </button>
      </div>
    </form>
  );
}
