import { Play, RotateCcw } from "lucide-react";
import { useNavigate } from "react-router-dom";
import ClinicalInput from "../components/Dashboard/ClinicalInput";
import { useAnalysis } from "../hooks/useAnalysis";
import { useEffect } from "react";

export default function AnalysisInputPage() {
  const { noteText, images, isAnalyzing, run, reset, result } = useAnalysis();
  const navigate = useNavigate();

  const hasInput = Boolean(noteText.trim() || images.length);

  // If already analyzing, redirect to processing page
  useEffect(() => {
    if (isAnalyzing) {
      navigate("/analysis/processing");
    }
  }, [isAnalyzing, navigate]);

  const handleRun = () => {
    run();
    navigate("/analysis/processing");
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      <section className="relative overflow-hidden rounded-[2rem] border border-white/70 bg-white/76 p-6 shadow-card backdrop-blur xl:p-8">
        <div className="pointer-events-none absolute right-0 top-0 h-56 w-56 rounded-full bg-brand-100/70 blur-3xl" />
        <div className="pointer-events-none absolute bottom-0 left-0 h-40 w-40 rounded-full bg-sky-100/70 blur-3xl" />

        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-xl">
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-brand-600">
              Step 1: Clinical Input
            </p>
            <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
              Enter patient data
            </h1>
            <p className="mt-3 text-sm leading-6 text-slate-500 sm:text-base">
              Submit note text and attach medical images. Once ready, run the analysis to extract ICD codes and generate reports.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={reset}
              className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-50"
            >
              <RotateCcw className="h-4 w-4" />
              Reset
            </button>

            <button
              onClick={handleRun}
              disabled={!hasInput}
              className="flex items-center gap-2 rounded-full bg-brand-600 px-6 py-3 text-sm font-semibold text-white shadow-soft transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Play className="h-4 w-4 fill-current" />
              Run analysis
            </button>
          </div>
        </div>
      </section>

      {result && !isAnalyzing && (
         <div className="rounded-[1.5rem] border border-brand-100 bg-brand-50 px-5 py-4 flex items-center justify-between">
           <p className="text-sm font-medium text-brand-800">
             You have an active analysis result.
           </p>
           <button
             onClick={() => navigate("/analysis/results")}
             className="text-sm font-semibold text-brand-600 hover:text-brand-700"
           >
             View Results &rarr;
           </button>
         </div>
      )}

      <div className="rounded-[2rem] border border-white/70 bg-white/88 p-6 shadow-card">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              Patient note and imaging context
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Supports text and multiple image attachments.
            </p>
          </div>
        </div>
        <ClinicalInput />
      </div>
    </div>
  );
}
