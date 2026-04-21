import { Clock, Trash2, ArrowRight, FileText } from "lucide-react";
import { useAnalysisState, useAnalysisDispatch } from "../context/AnalysisContext";
import { useNavigate } from "react-router-dom";
import type { AnalysisHistoryEntry } from "../api/types";

export default function HistoryPage() {
  const { history } = useAnalysisState();
  const dispatch = useAnalysisDispatch();
  const navigate = useNavigate();

  const loadEntry = (entry: AnalysisHistoryEntry) => {
    dispatch({ type: "LOAD_HISTORY_ENTRY", entry });
    navigate("/analysis/results");
  };

  return (
    <div className="w-full">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-400">
            History
          </p>
          <h1 className="mt-2 flex items-center gap-2 text-2xl font-semibold text-slate-900">
            <Clock className="w-6 h-6 text-brand-600" />
            Analysis History
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Previous analyses stored locally in your browser
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <span className="rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-600 shadow-sm">
            {history.length} saved locally
          </span>
          {history.length > 0 && (
            <button
              onClick={() => dispatch({ type: "CLEAR_HISTORY" })}
              className="flex items-center gap-2 rounded-full bg-red-50 px-4 py-2 text-sm font-semibold text-red-600 transition-colors hover:bg-red-100"
            >
              <Trash2 className="w-4 h-4" />
              Clear all
            </button>
          )}
        </div>
      </div>

      {history.length === 0 ? (
        <div className="flex h-[500px] flex-col items-center justify-center rounded-[2rem] border border-white/70 bg-white/88 p-8 text-slate-400 shadow-card">
          <div className="mb-6 flex h-32 w-32 items-center justify-center rounded-full bg-slate-50">
            <FileText className="w-10 h-10 text-slate-300" />
          </div>
          <p className="text-lg font-semibold text-slate-600">No history yet</p>
          <p className="mt-1 text-sm">Analyses you run will appear here</p>
        </div>
      ) : (
        <div className="rounded-[2rem] border border-white/70 bg-white/88 p-8 shadow-card">
          <div className="space-y-4">
            {history.map((entry) => (
              <div
                key={entry.id}
                className="group rounded-2xl border border-transparent bg-slate-50/80 p-5 transition-all hover:border-slate-200 hover:bg-white hover:shadow-card"
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div className="min-w-0 flex-1 pr-0 md:pr-6">
                    <p className="mb-2 truncate text-[15px] font-semibold text-slate-800">
                      {entry.note_preview}
                    </p>
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                        <Clock className="w-3 h-3" />
                        {new Date(entry.timestamp).toLocaleString()}
                      </span>
                      <span className="rounded-full bg-brand-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest text-brand-700">
                        {entry.response.mode} mode
                      </span>
                      <span className="text-[11px] font-semibold text-slate-500">
                        {entry.response.icd_codes.length} ICD codes
                      </span>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {entry.response.icd_codes.slice(0, 5).map((c) => (
                        <code
                          key={c.code}
                          className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-[11px] font-bold uppercase text-slate-700"
                        >
                          {c.code}
                        </code>
                      ))}
                      {entry.response.icd_codes.length > 5 && (
                        <span className="self-center text-[11px] font-semibold text-slate-400">
                          +{entry.response.icd_codes.length - 5} more
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => loadEntry(entry)}
                    className="flex shrink-0 items-center gap-2 rounded-full bg-brand-50 px-4 py-2 text-sm font-semibold text-brand-600 transition-all hover:bg-brand-100 md:opacity-0 md:group-hover:opacity-100"
                  >
                    Load Data
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
