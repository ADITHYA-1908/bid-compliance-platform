"use client";

import React from "react";
import { AlertTriangle, X } from "lucide-react";

interface ConfirmArchiveModalProps {
  isOpen: boolean;
  tenderNumber: string;
  tenderTitle: string;
  isSubmitting?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

export function ConfirmArchiveModal({
  isOpen,
  tenderNumber,
  tenderTitle,
  isSubmitting = false,
  onConfirm,
  onClose,
}: ConfirmArchiveModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-0">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity"
        onClick={!isSubmitting ? onClose : undefined}
      />

      {/* Modal Dialog */}
      <div className="relative transform overflow-hidden rounded-xl bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg border border-slate-200">
        <div className="bg-white px-6 pt-6 pb-4 sm:p-6 sm:pb-4">
          <div className="sm:flex sm:items-start gap-4">
            <div className="mx-auto flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-rose-100 sm:mx-0">
              <AlertTriangle className="h-6 w-6 text-rose-600" />
            </div>

            <div className="mt-3 text-center sm:mt-0 sm:text-left">
              <h3 className="text-base font-bold text-slate-900">
                Archive Tender Opportunity?
              </h3>
              <div className="mt-2 text-xs text-slate-600 space-y-2">
                <p>
                  Are you sure you want to archive tender{" "}
                  <span className="font-mono font-bold text-slate-900">{tenderNumber}</span> (
                  <span className="italic">{tenderTitle}</span>)?
                </p>
                <p className="rounded-md bg-amber-50 p-2.5 text-amber-800 border border-amber-200">
                  <strong>Notice:</strong> This tender will be soft-deleted and removed from active procurement listings. All associated compliance records will remain securely archived for audit integrity.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-slate-50 px-6 py-3.5 sm:flex sm:flex-row-reverse sm:px-6 gap-2 border-t border-slate-100">
          <button
            type="button"
            disabled={isSubmitting}
            onClick={onConfirm}
            className="inline-flex w-full justify-center rounded-md bg-rose-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-rose-700 disabled:opacity-50 sm:w-auto transition-colors cursor-pointer"
          >
            {isSubmitting ? "Archiving..." : "Confirm Archive"}
          </button>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={onClose}
            className="mt-2 sm:mt-0 inline-flex w-full justify-center rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 disabled:opacity-50 sm:w-auto transition-colors cursor-pointer"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
