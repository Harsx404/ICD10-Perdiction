import type { LucideIcon } from "lucide-react";
import {
  Activity,
  AlertTriangle,
  FileCode2,
  FileText,
  ShieldCheck,
  Star,
  Stethoscope,
} from "lucide-react";
import PdfViewer from "../PdfViewer";
import type { ClinicalAnalysisResponse } from "../../api/types";

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-400" : "bg-red-400";

  return (
    <div className="mt-3 flex items-center gap-3">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-10 text-right text-xs font-semibold text-slate-400">
        {pct}%
      </span>
    </div>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const cls = {
    low: "border-emerald-100 bg-emerald-50 text-emerald-700",
    moderate: "border-amber-100 bg-amber-50 text-amber-700",
    high: "border-red-100 bg-red-50 text-red-700",
  }[severity] || "border-slate-200 bg-slate-50 text-slate-700";

  return (
    <span className={`rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.18em] ${cls}`}>
      {severity}
    </span>
  );
}

function SectionHeader({
  icon: Icon,
  eyebrow,
  title,
}: {
  icon: LucideIcon;
  eyebrow: string;
  title: string;
}) {
  return (
    <div className="mb-4 flex items-center gap-3">
      <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
        <Icon className="h-5 w-5" />
      </span>
      <div>
        <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-400">
          {eyebrow}
        </p>
        <h3 className="mt-1 text-lg font-semibold text-slate-900">{title}</h3>
      </div>
    </div>
  );
}

function SummaryTile({
  icon: Icon,
  label,
  value,
  detail,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">
          {label}
        </p>
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-brand-600 shadow-sm">
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <p className="mt-3 text-base font-semibold text-slate-900">{value}</p>
      <p className="mt-1 text-sm text-slate-500">{detail}</p>
    </div>
  );
}

interface Props {
  result: ClinicalAnalysisResponse;
}

export default function ResultsPanels({ result }: Props) {
  const secondaryCodes = result.icd_codes.filter(
    (code) => code.code !== result.primary_icd_code?.code,
  );

  return (
    <div className="space-y-8">
      <div className="grid gap-3 md:grid-cols-3">
        <SummaryTile
          icon={ShieldCheck}
          label="Run Mode"
          value={result.mode === "full" ? "Full pipeline" : "Degraded mode"}
          detail={
            result.mode === "full"
              ? "All configured model-backed stages completed."
              : "At least one fallback path was used during analysis."
          }
        />
        <SummaryTile
          icon={FileCode2}
          label="Primary Output"
          value={result.primary_icd_code?.code ?? `${result.icd_codes.length} codes`}
          detail={
            result.primary_icd_code?.description ??
            "Primary ICD selection will appear when a best code is chosen."
          }
        />
        <SummaryTile
          icon={FileText}
          label="Report"
          value={result.doc_id ? "Saved PDF ready" : "Inline report ready"}
          detail={
            result.doc_id
              ? "The narrative report was persisted and can be viewed as PDF."
              : "Narrative output is available inline for this session."
          }
        />
      </div>

      {result.mode === "degraded" && (
        <div className="rounded-[1.5rem] border border-amber-100 bg-amber-50 p-4 text-sm text-amber-800">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-600" />
            <div>
              <p className="font-semibold">Degraded mode active</p>
              <p className="mt-1 leading-6">
                The app returned a valid response, but some model-backed stages were
                unavailable and fallback logic was used.
              </p>
            </div>
          </div>
        </div>
      )}

      <section>
        <SectionHeader
          icon={Stethoscope}
          eyebrow="Coding Output"
          title="Diagnostic Codes"
        />

        {result.primary_icd_code && (
          <div className="overflow-hidden rounded-[1.75rem] border border-brand-100 bg-brand-50/70 shadow-card">
            <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-start sm:justify-between sm:p-6">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1 rounded-full bg-white px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-brand-700 shadow-sm">
                    <Star className="h-3 w-3 fill-current" />
                    Primary selection
                  </span>
                  <span className="rounded-full border border-brand-100 bg-white/80 px-3 py-1 text-[11px] font-semibold text-brand-700">
                    {result.mode} mode
                  </span>
                </div>

                <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:gap-5">
                  <code className="w-fit rounded-2xl bg-white px-4 py-3 text-2xl font-black tracking-tight text-brand-700 shadow-sm">
                    {result.primary_icd_code.code}
                  </code>
                  <div className="min-w-0 flex-1">
                    <p className="text-lg font-semibold leading-tight text-slate-900">
                      {result.primary_icd_code.description}
                    </p>
                    {result.primary_icd_code.rationale && (
                      <p className="mt-2 text-sm leading-6 text-slate-600">
                        {result.primary_icd_code.rationale}
                      </p>
                    )}
                    <ConfidenceBar value={result.primary_icd_code.confidence} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          {secondaryCodes.map((code) => (
            <div
              key={code.code}
              className="rounded-[1.5rem] border border-slate-200 bg-white p-4 shadow-card"
            >
              <div className="flex gap-3">
                <code className="h-fit rounded-xl bg-slate-50 px-3 py-2 text-sm font-bold text-slate-800">
                  {code.code}
                </code>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-slate-800">
                    {code.description}
                  </p>
                  <ConfidenceBar value={code.confidence} />
                </div>
              </div>
            </div>
          ))}

          {result.icd_codes.length === 0 && (
            <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-5 text-sm text-slate-500 lg:col-span-2">
              No ICD codes were returned for this analysis.
            </div>
          )}
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <section>
          <SectionHeader
            icon={Activity}
            eyebrow="Clinical Reasoning"
            title="Differential Diagnosis"
          />
          <div className="space-y-3">
            {result.diagnosis.length > 0 ? (
              result.diagnosis.map((diagnosis) => (
                <div
                  key={`${diagnosis.label}-${diagnosis.probability}`}
                  className="rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-semibold text-slate-900">
                      {diagnosis.label}
                    </p>
                    <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-600">
                      {Math.round(diagnosis.probability * 100)}%
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-500">
                    {diagnosis.rationale}
                  </p>
                  <ConfidenceBar value={diagnosis.probability} />
                </div>
              ))
            ) : (
              <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-5 text-sm text-slate-500">
                No differential diagnoses were returned for this analysis.
              </div>
            )}
          </div>
        </section>

        <section>
          <SectionHeader
            icon={ShieldCheck}
            eyebrow="Risk Review"
            title="Risk Signals"
          />
          <div className="space-y-3">
            {result.risks.length > 0 ? (
              result.risks.map((risk) => (
                <div
                  key={`${risk.label}-${risk.severity}`}
                  className="rounded-[1.5rem] border border-slate-200 bg-white p-4 shadow-card"
                >
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={risk.severity} />
                    <span className="text-sm font-semibold text-slate-900">
                      {risk.label}
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-500">
                    {risk.rationale}
                  </p>
                </div>
              ))
            ) : (
              <div className="rounded-[1.5rem] border border-emerald-100 bg-emerald-50/80 p-5 text-sm font-semibold text-emerald-700">
                No elevated risk signals were detected.
              </div>
            )}
          </div>
        </section>
      </div>

      <section>
        <SectionHeader
          icon={Activity}
          eyebrow="Extraction"
          title="Extracted Clinical Entities"
        />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {(
            [
              ["Diseases", result.entities.diseases, "bg-indigo-50 text-indigo-700"],
              ["Symptoms", result.entities.symptoms, "bg-sky-50 text-sky-700"],
              ["Severity", result.entities.severity, "bg-violet-50 text-violet-700"],
              ["Complications", result.entities.complications, "bg-rose-50 text-rose-700"],
              ["Negations", result.entities.negations, "bg-slate-100 text-slate-600"],
            ] as const
          ).map(([label, items, badgeClass]) => (
            <div
              key={label}
              className="rounded-[1.5rem] border border-slate-200 bg-white p-4 shadow-card"
            >
              <div className="mb-4 flex items-center justify-between gap-3">
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-400">
                  {label}
                </p>
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-semibold text-slate-500">
                  {items.length}
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {items.length > 0 ? (
                  items.map((item) => (
                    <span
                      key={`${label}-${item}`}
                      className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${badgeClass}`}
                    >
                      {item}
                    </span>
                  ))
                ) : (
                  <span className="text-xs italic text-slate-300">none detected</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {result.validation_notes.length > 0 && (
        <section>
          <SectionHeader
            icon={AlertTriangle}
            eyebrow="Quality Checks"
            title="Validation Notes"
          />
          <div className="space-y-3">
            {result.validation_notes.map((note, index) => (
              <div
                key={`${index}-${note}`}
                className="rounded-[1.5rem] border border-amber-100 bg-amber-50 p-4 text-sm leading-6 text-amber-800"
              >
                {note}
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <SectionHeader
          icon={FileText}
          eyebrow="Report"
          title="Narrative Summary"
        />

        {result.doc_id ? (
          <div className="space-y-4">
            <div className="rounded-[1.5rem] border border-brand-100 bg-brand-50/70 p-4 text-sm leading-6 text-brand-800">
              This result has a saved PDF report. Use the embedded viewer below or download it directly.
            </div>
            <PdfViewer docId={result.doc_id} />
          </div>
        ) : (
          <div className="rounded-[1.75rem] border border-slate-200 bg-slate-50/80 p-6">
            <pre className="whitespace-pre-wrap font-sans text-sm leading-7 text-slate-700">
              {result.report}
            </pre>
          </div>
        )}
      </section>
    </div>
  );
}
