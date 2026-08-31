"use client";

import React, { useState, useEffect } from "react";
import {
  TenderRequirement,
  TenderRequirementCreatePayload,
  TenderRequirementUpdatePayload,
} from "@/lib/api";
import {
  REQUIREMENT_TEMPLATES,
  RequirementTemplate,
} from "@/config/requirementTemplates";
import { X, Sparkles, AlertCircle, Save, ShieldCheck } from "lucide-react";

interface RequirementModalProps {
  isOpen: boolean;
  tenderId: string;
  isDraft: boolean;
  editingRequirement?: TenderRequirement | null;
  isSubmitting?: boolean;
  serverError?: string | null;
  onSave: (payload: TenderRequirementCreatePayload | TenderRequirementUpdatePayload) => Promise<void>;
  onClose: () => void;
}

export function RequirementModal({
  isOpen,
  tenderId,
  isDraft,
  editingRequirement,
  isSubmitting = false,
  serverError = null,
  onSave,
  onClose,
}: RequirementModalProps) {
  const isEditMode = Boolean(editingRequirement);

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("STATUTORY");
  const [requirementType, setRequirementType] = useState("BOOLEAN");
  const [operator, setOperator] = useState("EQUALS");
  const [expectedValue, setExpectedValue] = useState<any>("");
  const [isMandatory, setIsMandatory] = useState(true);
  const [weight, setWeight] = useState("10");
  const [displayOrder, setDisplayOrder] = useState("0");

  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (editingRequirement) {
      setCode(editingRequirement.code || "");
      setName(editingRequirement.name || "");
      setDescription(editingRequirement.description || "");
      setCategory(editingRequirement.category || "STATUTORY");
      setRequirementType(editingRequirement.requirement_type || "BOOLEAN");
      setOperator(editingRequirement.operator || "EQUALS");
      setExpectedValue(
        editingRequirement.expected_value !== undefined && editingRequirement.expected_value !== null
          ? editingRequirement.expected_value
          : ""
      );
      setIsMandatory(editingRequirement.is_mandatory ?? true);
      setWeight(String(editingRequirement.weight ?? "10"));
      setDisplayOrder(String(editingRequirement.display_order ?? "0"));
    } else {
      // Default reset
      setCode("");
      setName("");
      setDescription("");
      setCategory("STATUTORY");
      setRequirementType("BOOLEAN");
      setOperator("EQUALS");
      setExpectedValue("");
      setIsMandatory(true);
      setWeight("10");
      setDisplayOrder("0");
    }
    setValidationError(null);
  }, [editingRequirement, isOpen]);

  if (!isOpen) return null;

  const handleApplyTemplate = (templateId: string) => {
    const tmpl = REQUIREMENT_TEMPLATES.find((t) => t.id === templateId);
    if (!tmpl) return;

    setCode(tmpl.code);
    setName(tmpl.name);
    setDescription(tmpl.description);
    setCategory(tmpl.category);
    setRequirementType(tmpl.requirement_type);
    setOperator(tmpl.operator);
    setExpectedValue(tmpl.expected_value);
    setIsMandatory(tmpl.is_mandatory);
    setWeight(String(tmpl.weight));
  };

  const handleTypeChange = (newType: string) => {
    setRequirementType(newType);
    if (newType === "DOCUMENT") {
      setOperator("EXISTS");
      setExpectedValue(true);
    } else if (newType === "BOOLEAN") {
      setOperator("EQUALS");
      setExpectedValue(true);
    } else if (newType === "NUMBER") {
      setOperator("GREATER_THAN_OR_EQUAL");
      setExpectedValue("0");
    } else {
      setOperator("EQUALS");
      setExpectedValue("");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (!code.trim()) {
      setValidationError("Requirement rule code is required (e.g. GST_REQUIRED).");
      return;
    }

    if (!name.trim()) {
      setValidationError("Requirement name is required.");
      return;
    }

    const numericWeight = parseFloat(weight);
    if (isNaN(numericWeight) || numericWeight < 0) {
      setValidationError("Weight must be a non-negative number.");
      return;
    }

    const numericOrder = parseInt(displayOrder, 10);
    if (isNaN(numericOrder) || numericOrder < 0) {
      setValidationError("Display order must be a non-negative integer.");
      return;
    }

    // Format expected value based on requirement type
    let parsedExpectedValue = expectedValue;
    if (requirementType === "NUMBER") {
      parsedExpectedValue = parseFloat(expectedValue);
      if (isNaN(parsedExpectedValue)) {
        setValidationError("Expected value must be a valid number for NUMBER criteria.");
        return;
      }
    } else if (requirementType === "BOOLEAN") {
      parsedExpectedValue = expectedValue === "true" || expectedValue === true;
    } else if (requirementType === "DOCUMENT" && (operator === "EXISTS" || operator === "NOT_EXISTS")) {
      parsedExpectedValue = operator === "EXISTS";
    }

    const payload: TenderRequirementCreatePayload | TenderRequirementUpdatePayload = {
      code: code.trim().toUpperCase(),
      name: name.trim(),
      description: description.trim() || null,
      category,
      requirement_type: requirementType,
      operator,
      expected_value: parsedExpectedValue,
      is_mandatory: isMandatory,
      weight: numericWeight,
      display_order: numericOrder,
    };

    await onSave(payload);
  };

  const displayError = validationError || serverError;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-0 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity"
        onClick={!isSubmitting ? onClose : undefined}
      />

      {/* Modal Dialog */}
      <div className="relative transform overflow-hidden rounded-xl bg-white text-left shadow-2xl transition-all sm:my-8 sm:w-full sm:max-w-2xl border border-slate-200 z-10 max-h-[90vh] flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 bg-slate-50">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-100 text-purple-900">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                {isEditMode ? "Edit Eligibility Requirement Rule" : "Add Eligibility / Compliance Requirement"}
              </h3>
              <p className="text-[11px] text-slate-500">
                Configure dynamic criteria rules evaluated during bidder compliance verification.
              </p>
            </div>
          </div>

          <button
            type="button"
            disabled={isSubmitting}
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSubmit} className="overflow-y-auto p-6 space-y-5 flex-1">
          {displayError && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3.5 text-xs text-red-800 flex items-start gap-2.5">
              <AlertCircle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold">Requirement Configuration Error</p>
                <p className="mt-0.5">{displayError}</p>
              </div>
            </div>
          )}

          {/* Quick Template Selector */}
          {!isEditMode && (
            <div className="rounded-lg bg-purple-50/75 p-3.5 border border-purple-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-purple-900 flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-purple-700" />
                  Pre-fill from Common GeM Template
                </span>
                <span className="text-[11px] text-purple-700">Quick Configuration</span>
              </div>

              <select
                onChange={(e) => handleApplyTemplate(e.target.value)}
                defaultValue=""
                className="block w-full rounded-md border border-purple-300 bg-white px-3 py-1.5 text-xs text-slate-900 focus:border-purple-600 focus:outline-none"
              >
                <option value="" disabled>
                  -- Select a Standard Criterion Template --
                </option>
                {REQUIREMENT_TEMPLATES.map((tmpl) => (
                  <option key={tmpl.id} value={tmpl.id}>
                    {tmpl.name} ({tmpl.category})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Form Fields Grid */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="reqCode" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                Rule Code <span className="text-red-500">*</span>
              </label>
              <input
                id="reqCode"
                type="text"
                required
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder="e.g. GST_REQUIRED, LOCAL_CONTENT"
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-mono text-slate-900 uppercase placeholder:text-slate-400 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
              />
              <p className="mt-1 text-[11px] text-slate-400">Unique uppercase identifier within this tender.</p>
            </div>

            <div>
              <label htmlFor="reqCategory" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                Category <span className="text-red-500">*</span>
              </label>
              <select
                id="reqCategory"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600 font-medium"
              >
                <option value="STATUTORY">Statutory & Regulatory</option>
                <option value="FINANCIAL">Financial Capability</option>
                <option value="TECHNICAL">Technical Specifications</option>
                <option value="EXPERIENCE">Past Performance & Experience</option>
                <option value="LOCAL_CONTENT">Local Content (Make in India)</option>
                <option value="DOCUMENT">Mandatory Documentation</option>
                <option value="BLACKLISTING">Debarment / Blacklisting</option>
                <option value="OTHER">Other Criteria</option>
              </select>
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="reqName" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                Requirement Title <span className="text-red-500">*</span>
              </label>
              <input
                id="reqName"
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Valid GST Registration Certificate"
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
              />
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="reqDesc" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                Detailed Evaluation Clause / Instructions
              </label>
              <textarea
                id="reqDesc"
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Specific verification criteria, expected document types, or threshold explanation..."
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
              />
            </div>

            {/* Rule Logic Specification */}
            <div>
              <label htmlFor="reqType" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                Data Type
              </label>
              <select
                id="reqType"
                value={requirementType}
                onChange={(e) => handleTypeChange(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600 font-medium"
              >
                <option value="BOOLEAN">Boolean (True / False)</option>
                <option value="NUMBER">Number (Financial / Quantity)</option>
                <option value="DOCUMENT">Document Upload</option>
                <option value="STATUS">Status Code (e.g. ACTIVE)</option>
                <option value="TEXT">Text String</option>
                <option value="DATE">Date</option>
              </select>
            </div>

            <div>
              <label htmlFor="reqOp" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                Evaluation Operator
              </label>
              <select
                id="reqOp"
                value={operator}
                onChange={(e) => setOperator(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600 font-medium"
              >
                {requirementType === "NUMBER" ? (
                  <>
                    <option value="GREATER_THAN_OR_EQUAL">&gt;= Greater Than or Equal</option>
                    <option value="GREATER_THAN">&gt; Greater Than</option>
                    <option value="EQUALS">= Equals</option>
                    <option value="LESS_THAN_OR_EQUAL">&lt;= Less Than or Equal</option>
                    <option value="LESS_THAN">&lt; Less Than</option>
                    <option value="NOT_EQUALS">!= Not Equals</option>
                  </>
                ) : requirementType === "DOCUMENT" ? (
                  <>
                    <option value="EXISTS">Must Exist / Be Uploaded</option>
                    <option value="NOT_EXISTS">Must Not Exist</option>
                  </>
                ) : requirementType === "BOOLEAN" ? (
                  <>
                    <option value="EQUALS">= Equals</option>
                    <option value="NOT_EQUALS">!= Not Equals</option>
                  </>
                ) : (
                  <>
                    <option value="EQUALS">= Equals</option>
                    <option value="CONTAINS">Contains</option>
                    <option value="NOT_EQUALS">!= Not Equals</option>
                  </>
                )}
              </select>
            </div>

            {/* Dynamic Expected Value Input */}
            <div className="sm:col-span-2">
              <label htmlFor="reqExpected" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                Expected Benchmark Value
              </label>
              {requirementType === "DOCUMENT" ? (
                <input
                  id="reqExpected"
                  type="text"
                  disabled
                  value="Document Certificate Required"
                  className="mt-1 block w-full rounded-lg border border-slate-200 bg-slate-100 px-3 py-2 text-xs text-slate-500 italic cursor-not-allowed"
                />
              ) : requirementType === "BOOLEAN" ? (
                <select
                  id="reqExpected"
                  value={String(expectedValue)}
                  onChange={(e) => setExpectedValue(e.target.value === "true")}
                  className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600 font-medium"
                >
                  <option value="true">True (Must be satisfied / Undertaking True)</option>
                  <option value="false">False (Must not be blacklisted / False)</option>
                </select>
              ) : requirementType === "NUMBER" ? (
                <input
                  id="reqExpected"
                  type="number"
                  step="any"
                  value={expectedValue}
                  onChange={(e) => setExpectedValue(e.target.value)}
                  placeholder="e.g. 50 (for 50%), 50000000 (for 5 Cr turnover)"
                  className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-mono text-slate-900 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
                />
              ) : (
                <input
                  id="reqExpected"
                  type="text"
                  value={expectedValue}
                  onChange={(e) => setExpectedValue(e.target.value)}
                  placeholder="e.g. ACTIVE"
                  className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
                />
              )}
            </div>

            {/* Weights and Order */}
            <div>
              <label htmlFor="reqWeight" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                Scoring Weight (Pts)
              </label>
              <input
                id="reqWeight"
                type="number"
                min="0"
                step="1"
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
                placeholder="10"
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-mono text-slate-900 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
              />
              <p className="mt-1 text-[11px] text-slate-400">Relative points contributing to compliance score.</p>
            </div>

            <div>
              <label htmlFor="reqOrder" className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                Display Order
              </label>
              <input
                id="reqOrder"
                type="number"
                min="0"
                step="1"
                value={displayOrder}
                onChange={(e) => setDisplayOrder(e.target.value)}
                placeholder="0"
                className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-mono text-slate-900 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
              />
            </div>

            {/* Mandatory Checkbox */}
            <div className="sm:col-span-2 pt-2">
              <label className="flex items-center gap-2 text-xs font-semibold text-slate-800 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={isMandatory}
                  onChange={(e) => setIsMandatory(e.target.checked)}
                  className="rounded border-slate-300 text-purple-900 focus:ring-purple-600 h-4 w-4"
                />
                <span>Mandatory Requirement (Disqualifies bid if failed)</span>
              </label>
              <p className="mt-0.5 pl-6 text-[11px] text-slate-500">
                If checked, non-compliance will flag this bidder as technically non-responsive.
              </p>
            </div>
          </div>

          {/* Modal Footer */}
          <div className="border-t border-slate-200 pt-4 flex items-center justify-end gap-2">
            <button
              type="button"
              disabled={isSubmitting}
              onClick={onClose}
              className="rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 disabled:opacity-50 transition-colors cursor-pointer"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-1.5 rounded-lg bg-purple-900 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-purple-800 disabled:opacity-50 transition-colors cursor-pointer"
            >
              {isSubmitting ? (
                <>Saving Rule...</>
              ) : (
                <>
                  <Save className="h-3.5 w-3.5" />
                  {isEditMode ? "Save Changes" : "Attach Requirement"}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
