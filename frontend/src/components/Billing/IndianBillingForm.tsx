import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import {
  BadgeIndianRupee,
  ClipboardList,
  FileText,
  ShieldCheck,
  WalletCards,
} from "lucide-react";
import type { ClinicalAnalysisResponse } from "../../api/types";

const inr = (n: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);

const STATES = [
  "Andhra Pradesh",
  "Arunachal Pradesh",
  "Assam",
  "Bihar",
  "Chhattisgarh",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Madhya Pradesh",
  "Maharashtra",
  "Manipur",
  "Meghalaya",
  "Mizoram",
  "Nagaland",
  "Odisha",
  "Punjab",
  "Rajasthan",
  "Sikkim",
  "Tamil Nadu",
  "Telangana",
  "Tripura",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal",
  "Delhi",
  "Jammu & Kashmir",
  "Ladakh",
  "Chandigarh",
  "Puducherry",
];

function estimateCost(icdCodes: string[]): { low: number; high: number } {
  if (icdCodes.length === 0) return { low: 500, high: 2000 };
  const code = icdCodes[0].toUpperCase();
  const chapter = code[0];
  const ranges: Record<string, [number, number]> = {
    A: [5000, 25000],
    B: [3000, 20000],
    C: [50000, 300000],
    D: [10000, 60000],
    E: [3000, 15000],
    F: [2000, 10000],
    G: [8000, 40000],
    H: [3000, 20000],
    I: [20000, 150000],
    J: [3000, 25000],
    K: [5000, 40000],
    L: [1000, 8000],
    M: [2000, 20000],
    N: [5000, 35000],
    O: [15000, 80000],
    S: [10000, 80000],
    Z: [500, 2000],
  };
  const [low, high] = ranges[chapter] ?? [2000, 15000];
  return { low, high };
}

interface FormData {
  patient_name: string;
  age: string;
  gender: "Male" | "Female" | "Other";
  phone: string;
  aadhaar: string;
  address: string;
  city: string;
  state: string;
  pin: string;
  scheme: string;
  policy_no: string;
  tpa_name: string;
  hospital_name: string;
  doctor_name: string;
  reg_no: string;
  hospital_phone: string;
  date_of_service: string;
  diagnosis: string;
  icd_codes: string;
  consultation_fee: string;
  investigation: string;
  medicine: string;
  procedure: string;
  room_charges: string;
}

interface Props {
  result: ClinicalAnalysisResponse | null;
  onSubmit?: (data: FormData) => void;
}

const SCHEMES = [
  "Self-Pay",
  "Ayushman Bharat / PMJAY",
  "CGHS",
  "ESIC",
  "State Government Scheme",
  "Private Health Insurance",
  "Corporate TPA",
  "Other",
];

const SPAN_CLASSES = {
  1: "md:col-span-1",
  2: "md:col-span-2",
  3: "md:col-span-3",
  4: "md:col-span-4",
} as const;

function Field({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
  required,
  span = 1,
  children,
}: {
  label: string;
  value?: string;
  onChange?: (v: string) => void;
  type?: string;
  placeholder?: string;
  required?: boolean;
  span?: 1 | 2 | 3 | 4;
  children?: ReactNode;
}) {
  return (
    <label className={`block ${SPAN_CLASSES[span]}`}>
      <span className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">
        {label}
        {required ? " *" : ""}
      </span>
      {children ?? (
        <input
          type={type}
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          placeholder={placeholder}
          required={required}
          className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm transition-colors placeholder:text-slate-300 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
        />
      )}
    </label>
  );
}

function Section({
  title,
  description,
  tone = "default",
  children,
}: {
  title: string;
  description: string;
  tone?: "default" | "brand";
  children: ReactNode;
}) {
  const shellClass =
    tone === "brand"
      ? "border-brand-100 bg-gradient-to-br from-brand-50 via-white to-sky-50"
      : "border-white/80 bg-white/88";

  return (
    <section className={`rounded-[2rem] border p-6 shadow-card ${shellClass}`}>
      <div className="mb-5">
        <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-slate-400">
          {title}
        </p>
        <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">{children}</div>
    </section>
  );
}

function SummaryTile({
  icon: Icon,
  label,
  value,
  helper,
}: {
  icon: typeof FileText;
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <div className="rounded-[1.75rem] border border-white/80 bg-white/90 p-5 shadow-card">
      <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
        <Icon className="h-5 w-5" />
      </div>
      <p className="mt-4 text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">
        {label}
      </p>
      <p className="mt-2 text-base font-semibold text-slate-900">{value}</p>
      <p className="mt-2 text-sm leading-6 text-slate-500">{helper}</p>
    </div>
  );
}

export default function IndianBillingForm({ result, onSubmit }: Props) {
  const icdList = result?.icd_codes.map((c) => c.code).join(", ") ?? "";
  const primaryDx = result?.primary_icd_code
    ? `${result.primary_icd_code.code} - ${result.primary_icd_code.description}`
    : result?.diagnosis?.[0]?.label ?? "";
  const { low, high } = estimateCost(result?.icd_codes.map((c) => c.code) ?? []);

  const [form, setForm] = useState<FormData>({
    patient_name: "",
    age: "",
    gender: "Male",
    phone: "",
    aadhaar: "",
    address: "",
    city: "",
    state: "",
    pin: "",
    scheme: "Self-Pay",
    policy_no: "",
    tpa_name: "",
    hospital_name: "",
    doctor_name: "",
    reg_no: "",
    hospital_phone: "",
    date_of_service: new Date().toISOString().split("T")[0],
    diagnosis: primaryDx,
    icd_codes: icdList,
    consultation_fee: "500",
    investigation: "",
    medicine: "",
    procedure: "",
    room_charges: "",
  });
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    setForm((current) => ({
      ...current,
      diagnosis: primaryDx || current.diagnosis,
      icd_codes: icdList || current.icd_codes,
    }));
  }, [icdList, primaryDx]);

  const set = (key: keyof FormData) => (value: string) =>
    setForm((current) => ({ ...current, [key]: value }));

  const total =
    (parseFloat(form.consultation_fee) || 0) +
    (parseFloat(form.investigation) || 0) +
    (parseFloat(form.medicine) || 0) +
    (parseFloat(form.procedure) || 0) +
    (parseFloat(form.room_charges) || 0);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit?.(form);
    setSubmitted(true);
    window.setTimeout(() => setSubmitted(false), 3000);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid gap-4 xl:grid-cols-3">
        <SummaryTile
          icon={ClipboardList}
          label="Clinical Input"
          value={result ? "Analysis linked" : "Manual entry"}
          helper={
            result
              ? "Diagnosis and ICD fields are prefilled from the current analysis."
              : "You can still draft a bill manually even without a loaded analysis."
          }
        />
        <SummaryTile
          icon={ShieldCheck}
          label="Coverage"
          value={form.scheme}
          helper="Switch between self-pay, public schemes, or private insurance before finalizing the bill."
        />
        <SummaryTile
          icon={BadgeIndianRupee}
          label="Estimated Range"
          value={result ? `${inr(low)} to ${inr(high)}` : "Add ICD output"}
          helper="The estimate is based on the lead ICD chapter and is intended as a rough billing guide."
        />
      </div>

      <Section
        title="Patient Details"
        description="Capture patient identity and contact details used across the bill and supporting paperwork."
      >
        <Field
          label="Full Name"
          value={form.patient_name}
          onChange={set("patient_name")}
          required
          span={2}
          placeholder="As per Aadhaar"
        />
        <Field label="Age" value={form.age} onChange={set("age")} placeholder="e.g. 45" />
        <Field label="Gender" required>
          <select
            value={form.gender}
            onChange={(e) =>
              setForm((current) => ({
                ...current,
                gender: e.target.value as FormData["gender"],
              }))
            }
            className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm transition-colors focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
          >
            <option>Male</option>
            <option>Female</option>
            <option>Other</option>
          </select>
        </Field>
        <Field
          label="Mobile"
          value={form.phone}
          onChange={set("phone")}
          placeholder="+91 98765 43210"
        />
        <Field
          label="Aadhaar / ID"
          value={form.aadhaar}
          onChange={set("aadhaar")}
          placeholder="XXXX XXXX XXXX"
        />
        <Field label="Address" value={form.address} onChange={set("address")} span={2} />
        <Field label="City" value={form.city} onChange={set("city")} />
        <Field label="State">
          <select
            value={form.state}
            onChange={(e) => set("state")(e.target.value)}
            className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm transition-colors focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
          >
            <option value="">Select state</option>
            {STATES.map((state) => (
              <option key={state}>{state}</option>
            ))}
          </select>
        </Field>
        <Field
          label="PIN Code"
          value={form.pin}
          onChange={set("pin")}
          placeholder="400001"
        />
      </Section>

      <Section
        title="Insurance / Scheme"
        description="Capture the payer and reference information used during reimbursement or settlement."
      >
        <Field label="Health Scheme" required>
          <select
            value={form.scheme}
            onChange={(e) => set("scheme")(e.target.value)}
            className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm transition-colors focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
          >
            {SCHEMES.map((scheme) => (
              <option key={scheme}>{scheme}</option>
            ))}
          </select>
        </Field>
        <Field
          label="Policy / Card No."
          value={form.policy_no}
          onChange={set("policy_no")}
          placeholder="Optional"
        />
        <Field
          label="TPA / Insurer"
          value={form.tpa_name}
          onChange={set("tpa_name")}
          placeholder="e.g. Medi Assist"
          span={2}
        />
      </Section>

      <Section
        title="Hospital / Provider"
        description="Enter provider details exactly as they should appear on the bill and claim paperwork."
      >
        <Field
          label="Hospital / Clinic"
          value={form.hospital_name}
          onChange={set("hospital_name")}
          required
          span={2}
        />
        <Field
          label="Treating Doctor"
          value={form.doctor_name}
          onChange={set("doctor_name")}
          required
          span={2}
        />
        <Field
          label="MCI Reg. No."
          value={form.reg_no}
          onChange={set("reg_no")}
          placeholder="MCI / NMC number"
          span={2}
        />
        <Field
          label="Hospital Phone"
          value={form.hospital_phone}
          onChange={set("hospital_phone")}
          span={2}
        />
      </Section>

      <Section
        title="Clinical Details"
        description="These fields can be auto-filled from analysis output and adjusted before bill generation."
        tone="brand"
      >
        <Field
          label="Date of Service"
          type="date"
          value={form.date_of_service}
          onChange={set("date_of_service")}
          required
        />
        <Field
          label="ICD-10 Codes"
          value={form.icd_codes}
          onChange={set("icd_codes")}
          span={3}
          placeholder="e.g. J45.41"
        />
        <Field
          label="Primary Diagnosis"
          value={form.diagnosis}
          onChange={set("diagnosis")}
          span={4}
        />
      </Section>

      <Section
        title="Charges"
        description="Enter the billable amounts in INR. The running total updates automatically."
      >
        <Field
          label="Consultation Fee (INR)"
          type="number"
          value={form.consultation_fee}
          onChange={set("consultation_fee")}
          placeholder="500"
        />
        <Field
          label="Investigations (INR)"
          type="number"
          value={form.investigation}
          onChange={set("investigation")}
          placeholder="0"
        />
        <Field
          label="Medicines (INR)"
          type="number"
          value={form.medicine}
          onChange={set("medicine")}
          placeholder="0"
        />
        <Field
          label="Procedures (INR)"
          type="number"
          value={form.procedure}
          onChange={set("procedure")}
          placeholder="0"
        />
        <Field
          label="Room Charges (INR)"
          type="number"
          value={form.room_charges}
          onChange={set("room_charges")}
          placeholder="0"
          span={3}
        />
      </Section>

      <div className="rounded-[2rem] border border-brand-200 bg-gradient-to-r from-brand-700 via-brand-600 to-sky-600 p-6 text-white shadow-soft">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-white/70">
              Billing Summary
            </p>
            <div className="mt-3 flex flex-wrap items-end gap-4">
              <p className="text-4xl font-black tracking-tight">{inr(total)}</p>
              {result ? (
                <p className="rounded-full border border-white/20 bg-white/10 px-3 py-1 text-sm text-white/85">
                  AI estimate: {inr(low)} to {inr(high)}
                </p>
              ) : null}
            </div>
            <p className="mt-3 text-sm leading-6 text-white/80">
              This page prepares a structured hospital bill draft. Server-side
              estimate and verification APIs can be integrated separately into the
              claim workflow.
            </p>
          </div>

          <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center">
            <div className="rounded-2xl border border-white/20 bg-white/10 px-4 py-3 text-sm text-white/85">
              <div className="flex items-center gap-2">
                <WalletCards className="h-4 w-4" />
                <span>{form.scheme}</span>
              </div>
            </div>
            <button
              type="submit"
              className="rounded-full bg-white px-6 py-3 text-sm font-bold text-brand-700 shadow-md transition-colors hover:bg-brand-50"
            >
              {submitted ? "Saved" : "Generate Bill"}
            </button>
          </div>
        </div>
      </div>
    </form>
  );
}
