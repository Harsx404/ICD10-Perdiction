import { useCallback, useRef } from "react";
import { ClipboardList, ImagePlus, Sparkles, Upload, X } from "lucide-react";
import { useAnalysisDispatch, useAnalysisState } from "../../context/AnalysisContext";

const SAMPLE_NOTE = `Patient is a 45-year-old male presenting with persistent cough for 3 weeks,
shortness of breath on exertion, and intermittent wheezing. No fever. History of mild
intermittent asthma diagnosed 10 years ago. Currently using albuterol PRN. Denies smoking.
No family history of COPD. Physical exam reveals bilateral expiratory wheezing.
O2 saturation 96% on room air. Peak flow 65% of predicted.`;

export default function ClinicalInput() {
  const { noteText, imagePreviews, isAnalyzing } = useAnalysisState();
  const dispatch = useAnalysisDispatch();
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files) return;
      const newFiles: File[] = [];
      const newPreviews: string[] = [];

      Array.from(files).forEach((file) => {
        if (!file.type.startsWith("image/")) return;
        newFiles.push(file);
        newPreviews.push(URL.createObjectURL(file));
      });

      if (newFiles.length > 0) {
        dispatch({ type: "ADD_IMAGES", files: newFiles, previews: newPreviews });
      }
    },
    [dispatch],
  );

  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      handleFiles(event.dataTransfer.files);
    },
    [handleFiles],
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2">
        {[
          { icon: ClipboardList, label: "SOAP notes" },
          { icon: Sparkles, label: "Encounter summaries" },
          { icon: ImagePlus, label: "Medical images" },
        ].map(({ icon: Icon, label }) => (
          <span
            key={label}
            className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-[11px] font-semibold text-slate-600"
          >
            <Icon className="h-3.5 w-3.5 text-brand-600" />
            {label}
          </span>
        ))}
      </div>

      <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <label className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-400">
              Clinical Note
            </label>
            <p className="mt-2 text-sm text-slate-500">
              Paste a visit summary, discharge note, triage note, or SOAP draft.
            </p>
          </div>
          <button
            onClick={() => dispatch({ type: "SET_NOTE", text: SAMPLE_NOTE })}
            className="inline-flex items-center gap-2 rounded-full border border-brand-100 bg-brand-50 px-3 py-2 text-xs font-semibold text-brand-700 transition-colors hover:bg-brand-100"
          >
            <Sparkles className="h-3.5 w-3.5" />
            Load sample case
          </button>
        </div>

        <textarea
          value={noteText}
          onChange={(event) => dispatch({ type: "SET_NOTE", text: event.target.value })}
          placeholder="Paste clinical note text here..."
          rows={9}
          disabled={isAnalyzing}
          className="mt-4 w-full resize-y rounded-[1.25rem] border border-white bg-white px-4 py-4 text-sm leading-6 text-slate-700 shadow-sm transition-all focus:border-brand-300 focus:bg-white disabled:opacity-50"
        />

        <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold text-slate-500">
              {noteText.length} characters
            </span>
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold text-slate-500">
              Note or image input is accepted
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Keep notes clinically specific for stronger ICD suggestions.
          </p>
        </div>
      </div>

      <div className="rounded-[1.5rem] border border-slate-200 bg-white p-4 shadow-card">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <label className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-400">
              Medical Images
            </label>
            <p className="mt-2 text-sm text-slate-500">
              Attach supporting image context such as scans, lesions, or photographed records.
            </p>
          </div>
          <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[11px] font-semibold text-slate-500">
            {imagePreviews.length} attached
          </span>
        </div>

        <div
          onDrop={handleDrop}
          onDragOver={(event) => event.preventDefault()}
          onClick={() => fileRef.current?.click()}
          className="group mt-4 cursor-pointer rounded-[1.5rem] border-2 border-dashed border-slate-200 bg-slate-50/70 p-8 text-center transition-colors hover:border-brand-200 hover:bg-brand-50/60"
        >
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-slate-400 shadow-sm transition-transform group-hover:scale-105 group-hover:text-brand-600">
            <Upload className="h-6 w-6" />
          </div>
          <p className="mt-4 text-sm font-semibold text-slate-700">
            Drag and drop images here, or browse files
          </p>
          <p className="mt-1 text-xs text-slate-400">
            PNG and JPEG files are accepted and encoded into the analysis request.
          </p>
        </div>

        <input
          ref={fileRef}
          type="file"
          multiple
          accept="image/*"
          className="hidden"
          onChange={(event) => handleFiles(event.target.files)}
        />

        {imagePreviews.length > 0 && (
          <div className="mt-5">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-400">
                Attached previews
              </p>
              <p className="text-xs text-slate-400">
                Remove any image before the next run if it should not be analyzed.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
              {imagePreviews.map((src, index) => (
                <div
                  key={index}
                  className="group relative overflow-hidden rounded-[1.25rem] border border-slate-200 bg-slate-50"
                >
                  <img
                    src={src}
                    alt={`Upload ${index + 1}`}
                    className="h-32 w-full object-cover"
                  />
                  <div className="absolute inset-0 bg-slate-950/35 opacity-0 transition-opacity group-hover:opacity-100" />
                  <button
                    onClick={(event) => {
                      event.stopPropagation();
                      dispatch({ type: "REMOVE_IMAGE", index });
                    }}
                    className="absolute right-3 top-3 inline-flex h-8 w-8 items-center justify-center rounded-full bg-white text-red-500 shadow-sm transition-transform hover:scale-105"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
