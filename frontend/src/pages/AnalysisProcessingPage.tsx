import { useNavigate } from "react-router-dom";
import PipelineVisualizer from "../components/Dashboard/PipelineVisualizer";
import { useAnalysis } from "../hooks/useAnalysis";
import { useEffect } from "react";
import { Square } from "lucide-react";

export default function AnalysisProcessingPage() {
  const { stages, isAnalyzing, cancel, result, error } = useAnalysis();
  const navigate = useNavigate();

  const completedStages = stages.filter((stage) => stage.status === "complete").length;

  useEffect(() => {
    // If analysis is done and we have a result, go to results page
    if (!isAnalyzing && result) {
      // Add a slight delay for better UX
      const timer = setTimeout(() => navigate("/analysis/results"), 1500);
      return () => clearTimeout(timer);
    }
    // If not analyzing and no result, redirect to input (unless there's an error)
    if (!isAnalyzing && !result && !error) {
      navigate("/analysis/input");
    }
  }, [isAnalyzing, result, error, navigate]);

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      <section className="relative overflow-hidden rounded-[2rem] border border-white/70 bg-white/76 p-6 shadow-card backdrop-blur xl:p-8">
        <div className="pointer-events-none absolute right-0 top-0 h-56 w-56 rounded-full bg-brand-100/70 blur-3xl" />
        <div className="pointer-events-none absolute bottom-0 left-0 h-40 w-40 rounded-full bg-emerald-100/70 blur-3xl" />

        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-xl">
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-brand-600">
              Step 2: Processing
            </p>
            <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
              Analyzing clinical data
            </h1>
            <p className="mt-3 text-sm leading-6 text-slate-500 sm:text-base">
              The AI pipeline is currently evaluating your input. Please wait while we process the medical text and imaging.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            {isAnalyzing && (
              <button
                onClick={cancel}
                className="flex items-center gap-2 rounded-full bg-red-50 px-5 py-3 text-sm font-semibold text-red-600 transition-colors hover:bg-red-100"
              >
                <Square className="h-4 w-4 fill-current" />
                Stop analysis
              </button>
            )}
          </div>
        </div>
      </section>

      {error && (
        <div className="rounded-[1.5rem] border border-red-100 bg-red-50 px-5 py-4 text-sm font-medium text-red-700">
          {error}
        </div>
      )}

      <div className="rounded-[2rem] border border-white/70 bg-white/88 p-6 shadow-card">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              Live Pipeline Status
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Processing checkpoints and intelligence modules.
            </p>
          </div>
          <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[11px] font-semibold text-slate-600">
            {completedStages}/{stages.length} complete
          </span>
        </div>
        <PipelineVisualizer stages={stages} />
      </div>
    </div>
  );
}
