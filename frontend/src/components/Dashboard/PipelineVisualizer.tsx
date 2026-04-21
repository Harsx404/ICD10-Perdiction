import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Circle,
  Loader2,
} from "lucide-react";
import { useState } from "react";
import type { StageState, StageStatus } from "../../api/types";

function StatusIcon({ status }: { status: StageStatus }) {
  switch (status) {
    case "idle":
      return <Circle className="h-5 w-5 text-slate-300" />;
    case "running":
      return <Loader2 className="h-5 w-5 animate-spin text-brand-600" />;
    case "complete":
      return <CheckCircle2 className="h-5 w-5 text-emerald-500" />;
    case "error":
      return <AlertCircle className="h-5 w-5 text-red-500" />;
  }
}

function statusLabel(status: StageStatus) {
  switch (status) {
    case "idle":
      return "Idle";
    case "running":
      return "Running";
    case "complete":
      return "Complete";
    case "error":
      return "Error";
  }
}

function statusTone(status: StageStatus) {
  switch (status) {
    case "idle":
      return {
        card: "border-slate-200 bg-slate-50/80",
        badge: "border-slate-200 bg-white text-slate-500",
        rail: "bg-slate-200",
      };
    case "running":
      return {
        card: "border-brand-100 bg-brand-50/80 shadow-soft",
        badge: "border-brand-100 bg-white text-brand-700",
        rail: "bg-brand-300",
      };
    case "complete":
      return {
        card: "border-emerald-100 bg-emerald-50/80",
        badge: "border-emerald-100 bg-white text-emerald-700",
        rail: "bg-emerald-300",
      };
    case "error":
      return {
        card: "border-red-100 bg-red-50/80",
        badge: "border-red-100 bg-white text-red-700",
        rail: "bg-red-200",
      };
  }
}

interface Props {
  stages: StageState[];
}

export default function PipelineVisualizer({ stages }: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const completedCount = stages.filter((stage) => stage.status === "complete").length;

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">Live stage timeline</h3>
          <p className="mt-1 text-sm text-slate-500">
            Each stage reports status, timing, and any streamed substeps.
          </p>
        </div>
        <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[11px] font-semibold text-slate-600">
          {completedCount}/{stages.length} complete
        </span>
      </div>

      <div className="space-y-3">
        {stages.map((stage, index) => {
          const tone = statusTone(stage.status);
          const isExpanded = Boolean(expanded[stage.id]);

          return (
            <div key={stage.id} className="relative pl-10">
              {index < stages.length - 1 && (
                <div className={`absolute left-3 top-10 h-[calc(100%+0.75rem)] w-0.5 ${tone.rail}`} />
              )}

              <div className="absolute left-0 top-3 flex h-6 w-6 items-center justify-center rounded-full border border-white bg-white text-[11px] font-bold text-slate-500 shadow-sm">
                {index + 1}
              </div>

              <div className={`rounded-[1.5rem] border p-4 transition-all ${tone.card}`}>
                <button
                  type="button"
                  onClick={() =>
                    setExpanded((current) => ({ ...current, [stage.id]: !current[stage.id] }))
                  }
                  className="flex w-full items-start gap-3 text-left"
                >
                  <span className="mt-0.5">
                    <StatusIcon status={stage.status} />
                  </span>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-slate-900">
                        {stage.label}
                      </span>
                      <span className={`rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.18em] ${tone.badge}`}>
                        {statusLabel(stage.status)}
                      </span>
                    </div>

                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                      <span>{stage.model}</span>
                      {stage.elapsed != null && <span>{stage.elapsed.toFixed(2)}s</span>}
                    </div>

                    {stage.detail && (
                      <p className="mt-2 text-sm text-slate-600">{stage.detail}</p>
                    )}
                  </div>

                  <span className="mt-0.5 text-slate-400">
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                  </span>
                </button>

                {isExpanded && stage.substeps.length > 0 && (
                  <div className="mt-4 space-y-2 border-t border-white/70 pt-4">
                    {stage.substeps.map((substep, substepIndex) => (
                      <div
                        key={`${stage.id}-${substepIndex}`}
                        className="rounded-xl bg-white/80 px-3 py-2 text-xs font-medium text-slate-600"
                      >
                        {substep}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
