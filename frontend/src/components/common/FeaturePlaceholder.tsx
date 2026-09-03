import React from "react";
import { Clock, Info, Layers, ShieldCheck } from "lucide-react";

interface FeaturePlaceholderProps {
  title: string;
  description: string;
  phase: string;
  moduleName?: string;
  plannedFeatures?: string[];
}

export function FeaturePlaceholder({
  title,
  description,
  phase,
  moduleName,
  plannedFeatures = [
    "GeM Procurement API schema compliance & field binding",
    "Automated clause-level audit trail & document verification",
    "Database model persistence with role-based access enforcement",
  ],
}: FeaturePlaceholderProps) {
  return (
    <div className="space-y-6">
      {/* Informational Banner */}
      <div className="rounded-2xl border border-blue-200 bg-blue-50/70 p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-900 text-white shadow-xs">
              <Clock className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-bold uppercase tracking-wider text-blue-950 font-heading">
                  {moduleName || title}
                </span>
                <span className="inline-flex items-center rounded-lg bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-800 border border-blue-200">
                  {phase}
                </span>
              </div>
              <p className="mt-1.5 text-xs text-slate-600 sm:text-sm leading-relaxed">
                {description}
              </p>
            </div>
          </div>

          <span className="inline-flex items-center gap-1.5 self-start sm:self-center rounded-full bg-amber-50 border border-amber-200 px-3 py-1.5 text-xs font-semibold text-amber-800 shadow-2xs">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
            Scheduled Implementation
          </span>
        </div>
      </div>

      {/* Feature Specs Grid */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
          <div className="flex items-center gap-2 mb-4">
            <Layers className="h-4 w-4 text-emerald-600" />
            <h3 className="text-sm font-bold text-slate-900 font-heading">Planned Module Architecture</h3>
          </div>
          <ul className="space-y-2.5 text-xs text-slate-600">
            {plannedFeatures.map((feat, idx) => (
              <li key={idx} className="flex items-start gap-2.5">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                <span>{feat}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            <h3 className="text-sm font-bold text-slate-900 font-heading">Security & RBAC Controls</h3>
          </div>
          <div className="space-y-2.5 text-xs text-slate-600 leading-relaxed">
            <p>• Server-side FastAPI role authorization verified via database.</p>
            <p>• Session lifecycle protected with cryptographically signed JWT tokens.</p>
            <p>• Full audit trail and integrity logging enabled upon phase activation.</p>
          </div>
        </div>
      </div>

      {/* Neutral Metric Indicators */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider font-heading">
            Module Telemetry & State
          </h3>
          <span className="text-xs text-slate-400">Data Source: Live Backend</span>
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-xl bg-slate-50 border border-slate-200 p-3.5">
            <span className="text-[11px] text-slate-500 font-medium">Records</span>
            <p className="mt-1.5 text-2xl font-bold text-slate-900 font-mono-score">—</p>
          </div>
          <div className="rounded-xl bg-slate-50 border border-slate-200 p-3.5">
            <span className="text-[11px] text-slate-500 font-medium">Pending Review</span>
            <p className="mt-1.5 text-2xl font-bold text-slate-900 font-mono-score">—</p>
          </div>
          <div className="rounded-xl bg-slate-50 border border-slate-200 p-3.5">
            <span className="text-[11px] text-slate-500 font-medium">Compliance Index</span>
            <p className="mt-1.5 text-2xl font-bold text-slate-900 font-mono-score">—</p>
          </div>
          <div className="rounded-xl bg-slate-50 border border-slate-200 p-3.5">
            <span className="text-[11px] text-slate-500 font-medium">Audit Status</span>
            <p className="mt-1.5 text-xs font-semibold text-amber-700">Awaiting Part Activation</p>
          </div>
        </div>
      </div>
    </div>
  );
}
