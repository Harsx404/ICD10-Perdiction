import { useEffect, useState } from "react";
import { FileText, RefreshCw } from "lucide-react";
import PdfViewer from "../components/PdfViewer";

interface AnalysisMeta {
  _id: string;
  created_at: string;
  note_text: string;
  version: number;
  fingerprint: string;
  response?: {
    mode?: string;
    primary_icd_code?: { code: string; description: string } | null;
  };
}

export default function ReportPage() {
  const [analyses, setAnalyses] = useState<AnalysisMeta[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchList = () => {
    setLoading(true);
    setError(null);

    fetch("/api/v1/analyses?limit=50")
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status}`);
        return response.json() as Promise<AnalysisMeta[]>;
      })
      .then((data) => {
        setAnalyses(data);
        if (data.length > 0 && !selected) setSelected(data[0]._id);
        setLoading(false);
      })
      .catch((fetchError) => {
        setError(fetchError.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fmt = (iso: string) => {
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  };

  return (
    <div className="w-full space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-400">
            Reports
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-slate-900">
            Saved PDF reports
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Review backend-persisted reports and reopen prior analyses from stored PDFs.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-600 shadow-sm">
            {analyses.length} saved analyses
          </span>
          <button
            onClick={fetchList}
            className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-600 shadow-sm transition-colors hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-[1.5rem] border border-red-100 bg-red-50 px-5 py-4 text-sm text-red-700">
          Could not load analyses: {error}
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
        <div className="rounded-[2rem] border border-white/70 bg-white/88 p-4 shadow-card">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-400">
              Saved documents
            </p>
            <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-semibold text-slate-500">
              Mongo-backed
            </span>
          </div>

          <div className="max-h-[720px] space-y-2 overflow-y-auto pr-1 scrollbar-hide">
            {loading && (
              <div className="flex min-h-[160px] items-center justify-center text-sm text-slate-400">
                Loading reports...
              </div>
            )}

            {!loading && analyses.length === 0 && (
              <div className="flex min-h-[220px] flex-col items-center justify-center gap-3 rounded-[1.5rem] bg-slate-50/80 p-6 text-center">
                <FileText className="h-10 w-10 text-slate-300" />
                <p className="text-sm font-semibold text-slate-600">No reports saved yet</p>
                <p className="text-sm text-slate-400">
                  Run an analysis with backend persistence enabled to populate this list.
                </p>
              </div>
            )}

            {analyses.map((analysis) => {
              const primaryCode = analysis.response?.primary_icd_code;
              const preview =
                analysis.note_text?.slice(0, 72) || "No note text available";
              const isActive = selected === analysis._id;

              return (
                <button
                  key={analysis._id}
                  onClick={() => setSelected(analysis._id)}
                  className={[
                    "w-full rounded-[1.5rem] border p-4 text-left transition-all",
                    isActive
                      ? "border-brand-100 bg-brand-50/80 shadow-card"
                      : "border-transparent bg-slate-50/80 hover:border-slate-200 hover:bg-white",
                  ].join(" ")}
                >
                  <div className="flex items-center justify-between gap-3">
                    {primaryCode ? (
                      <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-bold text-brand-700 shadow-sm">
                        {primaryCode.code}
                      </span>
                    ) : (
                      <span className="text-xs text-slate-400">No primary code</span>
                    )}
                    <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                      v{analysis.version}
                    </span>
                  </div>
                  <p className="mt-3 text-sm font-medium leading-6 text-slate-700">
                    {preview}
                  </p>
                  <p className="mt-3 text-xs text-slate-400">{fmt(analysis.created_at)}</p>
                </button>
              );
            })}
          </div>
        </div>

        <div className="min-w-0">
          {selected ? (
            <PdfViewer docId={selected} />
          ) : (
            <div className="flex min-h-[720px] flex-col items-center justify-center gap-3 rounded-[2rem] border border-white/70 bg-white/88 p-8 text-center shadow-card">
              <FileText className="h-12 w-12 text-slate-300" />
              <p className="text-lg font-semibold text-slate-700">Select a report to view</p>
              <p className="max-w-md text-sm leading-6 text-slate-400">
                Choose a saved analysis from the left to open its PDF report in the viewer.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
