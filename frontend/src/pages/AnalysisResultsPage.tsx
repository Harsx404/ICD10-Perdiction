import { useNavigate } from "react-router-dom";
import ResultsPanels from "../components/Dashboard/ResultsPanels";
import { useAnalysis } from "../hooks/useAnalysis";
import { useEffect } from "react";
import { ArrowLeft, RotateCcw } from "lucide-react";

export default function AnalysisResultsPage() {
  const { result, isAnalyzing, reset } = useAnalysis();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAnalyzing) {
      navigate("/analysis/processing");
    } else if (!result) {
      navigate("/analysis/input");
    }
  }, [isAnalyzing, result, navigate]);

  const handleStartNew = () => {
    reset();
    navigate("/analysis/input");
  };

  if (!result) return null;

  return (
    <div className="w-full space-y-6">
      <section className="relative overflow-hidden rounded-[2rem] border border-white/70 bg-white/76 p-6 shadow-card backdrop-blur xl:p-8">
        <div className="pointer-events-none absolute right-0 top-0 h-56 w-56 rounded-full bg-brand-100/70 blur-3xl" />
        <div className="pointer-events-none absolute bottom-0 left-0 h-40 w-40 rounded-full bg-emerald-100/70 blur-3xl" />

        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-xl">
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-brand-600">
              Step 3: Results
            </p>
            <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
              Analysis Output
            </h1>
            <p className="mt-3 text-sm leading-6 text-slate-500 sm:text-base">
              Review ICD recommendations, AI diagnosis narrative, risk profile, and finalized report.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => navigate("/analysis/input")}
              className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-50"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Input
            </button>
            <button
              onClick={handleStartNew}
              className="flex items-center gap-2 rounded-full bg-brand-600 px-6 py-3 text-sm font-semibold text-white shadow-soft transition-colors hover:bg-brand-700"
            >
              <RotateCcw className="h-4 w-4" />
              Start New Analysis
            </button>
          </div>
        </div>
      </section>

      <div className="rounded-[2rem] border border-white/70 bg-white/88 p-6 shadow-card sm:p-8">
        <ResultsPanels result={result} />
      </div>
    </div>
  );
}
