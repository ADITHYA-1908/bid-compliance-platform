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
      <div className="rounded-2xl border border-indigo-800/50 bg-indigo-950/40 p-5 backdrop-blur-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-700 to-purple-600 text-white shadow-md">
              <Clock className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-300">
                  {moduleName || title}
                </span>
                <span className="inline-flex items-center rounded-lg bg-indigo-950/80 px-2 py-0.5 text-[10px] font-bold text-indigo-300 border border-indigo-700/40">
                  {phase}
                </span>
              </div>
              <p className="mt-1.5 text-xs text-slate-400 sm:text-sm leading-relaxed">
                {description}
              </p>
            </div>
          </div>

          <span className="inline-flex items-center gap-1.5 self-start sm:self-center rounded-full bg-amber-950/60 border border-amber-700/40 px-3 py-1.5 text-xs font-semibold text-amber-300">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
            Scheduled Implementation
          </span>
        </div>
      </div>

      {/* Feature Specs Grid */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        <div className="glass-card rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Layers className="h-4 w-4 text-purple-400" />
            <h3 className="text-sm font-bold text-white">Planned Module Architecture</h3>
          </div>
          <ul className="space-y-2.5 text-xs text-slate-400">
            {plannedFeatures.map((feat, idx) => (
              <li key={idx} className="flex items-start gap-2.5">
                <span className="h-1.5 w-1.5 rounded-full bg-purple-500 mt-1.5 shrink-0" />
                <span>{feat}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="glass-card rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <h3 className="text-sm font-bold text-white">Security & RBAC Controls</h3>
          </div>
          <div className="space-y-2.5 text-xs text-slate-400 leading-relaxed">
            <p>• Server-side FastAPI role authorization verified via database.</p>
            <p>• Session lifecycle protected with cryptographically signed JWT tokens.</p>
            <p>• Full audit trail and integrity logging enabled upon phase activation.</p>
          </div>
        </div>
      </div>

      {/* Neutral Metric Indicators */}
      <div className="glass-panel rounded-2xl p-5">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
            Module Telemetry & State
          </h3>
          <span className="text-xs text-slate-500">Data Source: Live Backend</span>
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-xl bg-slate-800/60 border border-slate-700/60 p-3.5">
            <span className="text-[11px] text-slate-400 font-medium">Records</span>
            <p className="mt-1.5 text-2xl font-bold text-white font-mono">—</p>
          </div>
          <div className="rounded-xl bg-slate-800/60 border border-slate-700/60 p-3.5">
            <span className="text-[11px] text-slate-400 font-medium">Pending Review</span>
            <p className="mt-1.5 text-2xl font-bold text-white font-mono">—</p>
          </div>
          <div className="rounded-xl bg-slate-800/60 border border-slate-700/60 p-3.5">
            <span className="text-[11px] text-slate-400 font-medium">Compliance Index</span>
            <p className="mt-1.5 text-2xl font-bold text-white font-mono">—</p>
          </div>
          <div className="rounded-xl bg-slate-800/60 border border-slate-700/60 p-3.5">
            <span className="text-[11px] text-slate-400 font-medium">Audit Status</span>
            <p className="mt-1.5 text-sm font-semibold text-amber-300">Awaiting Part Activation</p>
          </div>
        </div>
      </div>
    </div>
  );
}
