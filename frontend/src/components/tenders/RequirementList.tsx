"use client";

import React, { useState } from "react";
import {
  TenderRequirement,
  TenderRequirementCreatePayload,
  TenderRequirementUpdatePayload,
} from "@/lib/api";
import { RequirementModal } from "./RequirementModal";
import { RuleVersionHistoryModal } from "./RuleVersionHistoryModal";
import { RuleReevaluationModal } from "./RuleReevaluationModal";
import { REQUIREMENT_TEMPLATES } from "@/config/requirementTemplates";
import { formatCurrency } from "@/lib/formatters";
import {
  PlusCircle,
  Edit2,
  Trash2,
  ShieldCheck,
  Sparkles,
  AlertTriangle,
  FileCheck,
  CheckCircle,
  HelpCircle,
  Lock,
  History,
  GitCompare,
  RefreshCw,
} from "lucide-react";

interface RequirementListProps {
  tenderId: string;
  isDraft: boolean;
  status?: string;
  requirements: TenderRequirement[];
  onAddRequirement: (payload: TenderRequirementCreatePayload) => Promise<void>;
  onUpdateRequirement: (requirementId: string, payload: TenderRequirementUpdatePayload) => Promise<void>;
  onDisableRequirement: (requirementId: string) => Promise<void>;
}

export function RequirementList({
  tenderId,
  isDraft,
  status = "DRAFT",
  requirements,
  onAddRequirement,
  onUpdateRequirement,
  onDisableRequirement,
}: RequirementListProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingReq, setEditingReq] = useState<TenderRequirement | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // Version history & re-evaluation state
  const [historyReq, setHistoryReq] = useState<TenderRequirement | null>(null);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isReevaluateAllOpen, setIsReevaluateAllOpen] = useState(false);

  // Disable confirmation state
  const [deactivatingReq, setDeactivatingReq] = useState<TenderRequirement | null>(null);
  const [isDeactivating, setIsDeactivating] = useState(false);

  // Total weight calculation
  const totalWeight = requirements
    .filter((r) => r.is_active)
    .reduce((sum, r) => sum + (r.weight ? Number(r.weight) : 0), 0);

  const mandatoryCount = requirements.filter((r) => r.is_active && r.is_mandatory).length;

  const handleOpenAdd = () => {
    setEditingReq(null);
    setModalError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (req: TenderRequirement) => {
    setEditingReq(req);
    setModalError(null);
    setIsModalOpen(true);
  };

  const handleOpenHistory = (req: TenderRequirement) => {
    setHistoryReq(req);
    setIsHistoryOpen(true);
  };

  const handleQuickAddTemplate = async (templateId: string) => {
    const tmpl = REQUIREMENT_TEMPLATES.find((t) => t.id === templateId);
    if (!tmpl) return;

    try {
      await onAddRequirement({
        code: tmpl.code,
        name: tmpl.name,
        description: tmpl.description,
        category: tmpl.category,
        requirement_type: tmpl.requirement_type,
        operator: tmpl.operator,
        expected_value: tmpl.expected_value,
        is_mandatory: tmpl.is_mandatory,
        weight: tmpl.weight,
        display_order: requirements.length + 1,
      });
    } catch (err: any) {
      alert(err?.message || "Failed to add template requirement.");
    }
  };

  const handleModalSave = async (
    payload: TenderRequirementCreatePayload | TenderRequirementUpdatePayload
  ) => {
    setIsSubmitting(true);
    setModalError(null);
    try {
      if (editingReq) {
        await onUpdateRequirement(editingReq.id, payload as TenderRequirementUpdatePayload);
      } else {
        await onAddRequirement(payload as TenderRequirementCreatePayload);
      }
      setIsModalOpen(false);
    } catch (err: any) {
      setModalError(err?.message || "Failed to save requirement rule.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmDisable = async () => {
    if (!deactivatingReq) return;
    setIsDeactivating(true);
    try {
      await onDisableRequirement(deactivatingReq.id);
      setDeactivatingReq(null);
    } catch (err: any) {
      alert(err?.message || "Failed to disable requirement.");
    } finally {
      setIsDeactivating(false);
    }
  };

  const formatCondition = (req: TenderRequirement) => {
    const { requirement_type, operator, expected_value, category } = req;

    if (requirement_type === "DOCUMENT" || operator === "EXISTS") {
      return (
        <span className="inline-flex items-center gap-1 text-slate-700 font-medium">
          <FileCheck className="h-3.5 w-3.5 text-blue-600" />
          Document Certificate Required
        </span>
      );
    }

    if (requirement_type === "BOOLEAN") {
      if (expected_value === false || expected_value === "false") {
        return <span className="font-mono text-emerald-700 font-semibold">= false (No Blacklisting)</span>;
      }
      return <span className="font-mono text-slate-900 font-semibold">= true (Required Undertaking)</span>;
    }

    if (requirement_type === "NUMBER") {
      let opSymbol = ">=";
      if (operator === "GREATER_THAN") opSymbol = ">";
      if (operator === "EQUALS") opSymbol = "=";
      if (operator === "LESS_THAN_OR_EQUAL") opSymbol = "<=";
      if (operator === "LESS_THAN") opSymbol = "<";

      if (category === "FINANCIAL") {
        return (
          <span className="font-mono font-semibold text-slate-900">
            {opSymbol} {formatCurrency(expected_value)}
          </span>
        );
      }
      if (category === "LOCAL_CONTENT") {
        return (
          <span className="font-mono font-semibold text-purple-900">
            {opSymbol} {expected_value}%
          </span>
        );
      }
      return (
        <span className="font-mono font-semibold text-slate-900">
          {opSymbol} {expected_value}
        </span>
      );
    }

    return (
      <span className="font-mono font-semibold text-slate-800">
        = {String(expected_value)}
      </span>
    );
  };

  const formatCategoryBadge = (category: string) => {
    switch (category) {
      case "STATUTORY":
        return <span className="rounded bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-blue-700 border border-blue-200">Statutory</span>;
      case "FINANCIAL":
        return <span className="rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700 border border-emerald-200">Financial</span>;
      case "TECHNICAL":
        return <span className="rounded bg-indigo-50 px-2 py-0.5 text-[10px] font-bold text-indigo-700 border border-indigo-200">Technical</span>;
      case "EXPERIENCE":
        return <span className="rounded bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-800 border border-amber-200">Experience</span>;
      case "LOCAL_CONTENT":
        return <span className="rounded bg-purple-50 px-2 py-0.5 text-[10px] font-bold text-purple-800 border border-purple-200">Make in India</span>;
      case "DOCUMENT":
        return <span className="rounded bg-cyan-50 px-2 py-0.5 text-[10px] font-bold text-cyan-800 border border-cyan-200">Document</span>;
      case "BLACKLISTING":
        return <span className="rounded bg-rose-50 px-2 py-0.5 text-[10px] font-bold text-rose-800 border border-rose-200">Debarment</span>;
      default:
        return <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-700">{category}</span>;
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-5">
      {/* Header with Title and Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-purple-900" />
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Eligibility & Compliance Rules ({requirements.length})
            </h3>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Dynamic criteria stored as rule data. Future Compliance Engine evaluates bidder submissions against these conditions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {requirements.length > 0 && (
            <button
              type="button"
              onClick={() => setIsReevaluateAllOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-purple-200 bg-purple-50 px-3 py-1.5 text-xs font-semibold text-purple-900 hover:bg-purple-100 transition-colors cursor-pointer shrink-0"
              title="Re-evaluate all submitted bids against active rule versions"
            >
              <RefreshCw className="h-3.5 w-3.5 text-purple-700" />
              Re-evaluate All Rules
            </button>
          )}

          {isDraft ? (
            <button
              type="button"
              onClick={handleOpenAdd}
              className="inline-flex items-center gap-1.5 rounded-lg bg-purple-900 px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-purple-800 transition-colors cursor-pointer shrink-0"
            >
              <PlusCircle className="h-4 w-4" />
              Add Custom Rule
            </button>
          ) : (
            <div className="inline-flex items-center gap-1.5 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 border border-slate-200 shrink-0">
              <Lock className="h-3.5 w-3.5 text-slate-500" />
              Requirements Locked
            </div>
          )}
        </div>
      </div>

      {/* Locked Status Notice */}
      {!isDraft && (
        <div className="flex items-center gap-2.5 rounded-lg bg-amber-50/80 p-3 border border-amber-200 text-xs text-amber-900">
          <Lock className="h-4 w-4 text-amber-700 shrink-0" />
          <span>
            Eligibility & compliance rules are <strong>locked</strong> because this tender is in <strong>{status}</strong> status. Rules cannot be modified after drafting to ensure fair evaluation.
          </span>
        </div>
      )}

      {/* Weight Summary Banner */}
      {requirements.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 rounded-lg bg-slate-50 p-3.5 border border-slate-200 text-xs">
          <div>
            <span className="text-slate-500 block text-[11px]">Total Active Criteria</span>
            <span className="font-bold text-slate-900 font-mono text-sm">{requirements.length} Rules</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[11px]">Mandatory Conditions</span>
            <span className="font-bold text-red-700 font-mono text-sm">{mandatoryCount} Disqualifying</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[11px]">Configured Scoring Weight</span>
            <span className="font-bold text-purple-950 font-mono text-sm">{totalWeight} Points</span>
          </div>
        </div>
      )}

      {/* Requirement Table */}
      {requirements.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center bg-slate-50/50 space-y-4">
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-purple-100 text-purple-900">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900">No Eligibility Requirements Configured</h4>
            <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
              Add statutory, financial, technical, or tender-specific rules before publishing this tender.
            </p>
          </div>

          {isDraft && (
            <div className="space-y-3 pt-2">
              <div className="flex flex-wrap items-center justify-center gap-2 max-w-xl mx-auto">
                <span className="text-[11px] font-semibold text-slate-500 w-full mb-1">
                  Quick-add standard requirements:
                </span>
                {REQUIREMENT_TEMPLATES.slice(0, 5).map((tmpl) => (
                  <button
                    key={tmpl.id}
                    type="button"
                    onClick={() => handleQuickAddTemplate(tmpl.id)}
                    className="inline-flex items-center gap-1 rounded-md border border-purple-200 bg-white px-2.5 py-1 text-[11px] font-medium text-purple-900 shadow-2xs hover:bg-purple-50 transition-colors cursor-pointer"
                  >
                    <PlusCircle className="h-3 w-3 text-purple-700" />
                    {tmpl.name.split(" ")[0]} ({tmpl.code})
                  </button>
                ))}
              </div>

              <div className="pt-2">
                <button
                  type="button"
                  onClick={handleOpenAdd}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-purple-900 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-purple-800 transition-colors cursor-pointer"
                >
                  <PlusCircle className="h-3.5 w-3.5" />
                  Add Custom Requirement
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider">
              <tr>
                <th scope="col" className="px-4 py-3 w-12 text-center">
                  #
                </th>
                <th scope="col" className="px-4 py-3">
                  Requirement Code & Title
                </th>
                <th scope="col" className="px-4 py-3">
                  Category
                </th>
                <th scope="col" className="px-4 py-3">
                  Verification Condition
                </th>
                <th scope="col" className="px-4 py-3 text-center">
                  Mandatory
                </th>
                <th scope="col" className="px-4 py-3 text-right">
                  Weight
                </th>
                <th scope="col" className="px-4 py-3 text-right">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white text-slate-700">
              {requirements.map((req, idx) => (
                <tr key={req.id} className="hover:bg-slate-50/75 transition-colors">
                  <td className="px-4 py-3.5 text-center font-mono text-slate-400 font-medium">
                    {req.display_order || idx + 1}
                  </td>

                  <td className="px-4 py-3.5 max-w-xs sm:max-w-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] font-bold text-slate-800 bg-slate-100 px-1.5 py-0.5 rounded">
                        {req.code}
                      </span>
                      <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                        v{req.current_version_number || 1}
                      </span>
                    </div>
                    <div className="font-semibold text-slate-900 mt-1">{req.name}</div>
                    {req.description && (
                      <div className="text-[11px] text-slate-500 line-clamp-1 mt-0.5" title={req.description}>
                        {req.description}
                      </div>
                    )}
                  </td>

                  <td className="px-4 py-3.5 whitespace-nowrap">
                    {formatCategoryBadge(req.category)}
                  </td>

                  <td className="px-4 py-3.5 whitespace-nowrap text-xs">
                    {formatCondition(req)}
                  </td>

                  <td className="px-4 py-3.5 whitespace-nowrap text-center">
                    {req.is_mandatory ? (
                      <span className="inline-flex rounded-md bg-red-50 px-2 py-0.5 text-[10px] font-bold text-red-700 border border-red-200">
                        Mandatory
                      </span>
                    ) : (
                      <span className="inline-flex rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
                        Optional
                      </span>
                    )}
                  </td>

                  <td className="px-4 py-3.5 whitespace-nowrap text-right font-mono font-semibold text-slate-900">
                    {Number(req.weight || 0)} Pts
                  </td>

                  <td className="px-4 py-3.5 whitespace-nowrap text-right">
                    <div className="inline-flex items-center gap-1.5 justify-end">
                      <button
                        type="button"
                        onClick={() => handleOpenHistory(req)}
                        className="inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 transition-colors cursor-pointer"
                        title="View Rule Version History"
                      >
                        <History className="h-3 w-3" />
                        History
                      </button>

                      {isDraft && (
                        <>
                          <button
                            type="button"
                            onClick={() => handleOpenEdit(req)}
                            className="rounded p-1 text-slate-500 hover:bg-purple-50 hover:text-purple-900 transition-colors cursor-pointer"
                            title="Edit Requirement Rule"
                          >
                            <Edit2 className="h-3.5 w-3.5" />
                          </button>

                          <button
                            type="button"
                            onClick={() => setDeactivatingReq(req)}
                            className="rounded p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600 transition-colors cursor-pointer"
                            title="Disable Requirement"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add / Edit Modal */}
      <RequirementModal
        isOpen={isModalOpen}
        tenderId={tenderId}
        isDraft={isDraft}
        editingRequirement={editingReq}
        isSubmitting={isSubmitting}
        serverError={modalError}
        onSave={handleModalSave}
        onClose={() => setIsModalOpen(false)}
      />

      {/* Disable Confirmation Modal */}
      {deactivatingReq && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-0">
          <div
            className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs"
            onClick={() => !isDeactivating && setDeactivatingReq(null)}
          />
          <div className="relative transform overflow-hidden rounded-xl bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-md border border-slate-200 p-6 space-y-4">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-rose-100 text-rose-600">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">Disable Eligibility Requirement?</h3>
                <p className="text-xs text-slate-600 mt-1">
                  Are you sure you want to disable{" "}
                  <span className="font-mono font-bold text-slate-900">{deactivatingReq.code}</span> (
                  {deactivatingReq.name})?
                </p>
                <p className="mt-2 text-[11px] text-amber-800 bg-amber-50 p-2 rounded border border-amber-200">
                  This rule will no longer be included in bidder compliance evaluation.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                disabled={isDeactivating}
                onClick={() => setDeactivatingReq(null)}
                className="rounded-lg border border-slate-300 bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isDeactivating}
                onClick={handleConfirmDisable}
                className="rounded-lg bg-rose-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 transition-colors cursor-pointer"
              >
                {isDeactivating ? "Disabling..." : "Confirm Disable"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Version History Modal */}
      {historyReq && (
        <RuleVersionHistoryModal
          isOpen={isHistoryOpen}
          onClose={() => {
            setIsHistoryOpen(false);
            setHistoryReq(null);
          }}
          tenderId={tenderId}
          tenderNumber={tenderId.slice(0, 8).toUpperCase()}
          requirementId={historyReq.id}
          requirementCode={historyReq.code}
          requirementName={historyReq.name}
        />
      )}

      {/* Tender-wide Re-evaluation Modal */}
      <RuleReevaluationModal
        isOpen={isReevaluateAllOpen}
        onClose={() => setIsReevaluateAllOpen(false)}
        tenderId={tenderId}
        tenderNumber={tenderId.slice(0, 8).toUpperCase()}
      />
    </div>
  );
}
