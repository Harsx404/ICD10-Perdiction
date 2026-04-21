import { useAnalysisState } from "../context/AnalysisContext";
import IndianBillingForm from "../components/Billing/IndianBillingForm";
import {
  AlertTriangle,
  FileText,
  IndianRupee,
  ShieldCheck,
  Stethoscope,
} from "lucide-react";

function BillingStat({
  label,
  value,
  helper,
}: {
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <div className="rounded-[1.75rem] border border-white/80 bg-white/88 p-5 shadow-card">
      <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">
        {label}
      </p>
      <p className="mt-3 text-base font-semibold text-slate-900">{value}</p>
      <p className="mt-2 text-sm leading-6 text-slate-500">{helper}</p>
    </div>
  );
}

export default function BillingPage() {
  const { result } = useAnalysisState();

  return (
    <div className="w-full max-w-[1400px]">
      <section className="rounded-[2rem] border border-white/80 bg-white/80 p-6 shadow-card backdrop-blur xl:p-8">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-brand-100 bg-brand-50 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.2em] text-brand-700">
              <IndianRupee className="h-3.5 w-3.5" />
              Billing Workspace
            </div>
            <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-900">
              Patient billing draft
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-500">
              Build a cleaner hospital bill draft from the current analysis
              session. Clinical output is used to prefill diagnosis and ICD
              fields, while provider and payer details stay editable.
            </p>
          </div>

          <div className="rounded-[1.75rem] border border-brand-100 bg-gradient-to-br from-brand-50 via-white to-sky-50 p-4 shadow-card">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-soft">
                <Stethoscope className="h-5 w-5" />
              </div>
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-brand-600">
                  Active Coding Output
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-900">
                  {result?.primary_icd_code?.code ?? "No ICD selected yet"}
                </p>
                <p className="mt-1 max-w-[260px] text-xs leading-5 text-slate-500">
                  {result?.primary_icd_code?.description ??
                    "Run an analysis first to prefill the clinical billing fields."}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <BillingStat
            label="Primary ICD"
            value={result?.primary_icd_code?.code ?? "Waiting for analysis"}
            helper="The billing form uses the current session output and keeps the fields editable."
          />
          <BillingStat
            label="Draft Type"
            value="Indian billing form"
            helper="The current UI focuses on bill drafting for hospital and clinic workflows."
          />
          <BillingStat
            label="Backend Support"
            value="Estimate and verify APIs"
            helper="The app can call billing estimate and verification endpoints even if this page stays focused on draft creation."
          />
        </div>
      </section>

      {!result && (
        <div className="mt-6 flex items-start gap-3 rounded-[1.75rem] border border-amber-200 bg-amber-50/90 p-4 text-sm text-amber-800 shadow-sm">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <div>
            <p className="font-semibold">No analysis loaded yet.</p>
            <p className="mt-1 leading-6">
              Run an analysis on the Analysis page first if you want ICD codes
              and diagnosis fields to be auto-filled here.
            </p>
          </div>
        </div>
      )}

      <section className="mt-6 rounded-[2rem] border border-white/80 bg-white/72 p-4 shadow-card backdrop-blur sm:p-6">
        <div className="mb-5 flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2 text-slate-900">
              <FileText className="h-5 w-5 text-brand-600" />
              <h2 className="text-lg font-semibold">Billing form</h2>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              Complete patient, provider, and charge details before generating the
              draft bill.
            </p>
          </div>
          <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-600">
            <span className="inline-flex items-center gap-2">
              <ShieldCheck className="h-3.5 w-3.5 text-brand-600" />
              Manual review still required
            </span>
          </div>
        </div>

        <IndianBillingForm result={result ?? null} />
      </section>
    </div>
  );
}
