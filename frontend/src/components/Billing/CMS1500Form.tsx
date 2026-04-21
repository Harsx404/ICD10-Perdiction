import { useState } from "react";
import type { PatientInfo, InsuranceInfo, ProviderInfo } from "../../api/types";

interface Props {
  icdCodes: string[];
  onSubmit: (data: {
    patient: PatientInfo;
    insurance: InsuranceInfo;
    provider: ProviderInfo;
    icd_codes: string[];
    cpt_codes: string[];
    date_of_service: string;
    place_of_service: string;
    total_charge: number;
    authorization_number?: string;
  }) => void;
  isLoading: boolean;
}

const defaultPatient: PatientInfo = {
  name: "",
  dob: "",
  gender: "M",
  address: "",
  city: "",
  state: "",
  zip: "",
  phone: "",
  ssn: "",
};

const defaultInsurance: InsuranceInfo = {
  payer_name: "",
  payer_id: "",
  member_id: "",
  group_number: "",
  plan_type: "Commercial",
};

const defaultProvider: ProviderInfo = {
  name: "",
  npi: "",
  tax_id: "",
  address: "",
  city: "",
  state: "",
  zip: "",
  phone: "",
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset className="border border-gray-100 rounded-2xl p-5 bg-gray-50/50">
      <legend className="text-[11px] font-bold text-gray-400 uppercase tracking-widest px-2 bg-white rounded-full mx-2 shadow-sm border border-gray-100">
        {title}
      </legend>
      {children}
    </fieldset>
  );
}

function Input({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
  required,
  className = "",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
  required?: boolean;
  className?: string;
}) {
  return (
    <label className={`block ${className}`}>
      <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">{label}{required && " *"}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        className="mt-1 w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
      />
    </label>
  );
}

export default function CMS1500Form({ icdCodes, onSubmit, isLoading }: Props) {
  const [patient, setPatient] = useState(defaultPatient);
  const [insurance, setInsurance] = useState(defaultInsurance);
  const [provider, setProvider] = useState(defaultProvider);
  const [cptCodes, setCptCodes] = useState("");
  const [dateOfService, setDateOfService] = useState(
    new Date().toISOString().split("T")[0],
  );
  const [placeOfService, setPlaceOfService] = useState("11");
  const [totalCharge, setTotalCharge] = useState("");
  const [authNumber, setAuthNumber] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      patient,
      insurance,
      provider,
      icd_codes: icdCodes,
      cpt_codes: cptCodes.split(",").map((s) => s.trim()).filter(Boolean),
      date_of_service: dateOfService,
      place_of_service: placeOfService,
      total_charge: parseFloat(totalCharge) || 0,
      authorization_number: authNumber || undefined,
    });
  };

  const pf = (field: keyof PatientInfo) => (v: string) =>
    setPatient((p) => ({ ...p, [field]: v }));
  const inf = (field: keyof InsuranceInfo) => (v: string) =>
    setInsurance((p) => ({ ...p, [field]: v }));
  const prf = (field: keyof ProviderInfo) => (v: string) =>
    setProvider((p) => ({ ...p, [field]: v }));

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Patient */}
      <Section title="Patient Information">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Input label="Full Name" value={patient.name} onChange={pf("name")} required className="col-span-2" />
          <Input label="DOB" type="date" value={patient.dob} onChange={pf("dob")} required />
          <label className="block">
            <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Gender *</span>
            <select
              value={patient.gender}
              onChange={(e) => setPatient((p) => ({ ...p, gender: e.target.value as "M" | "F" | "O" }))}
              className="mt-1 w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
            >
              <option value="M">Male</option>
              <option value="F">Female</option>
              <option value="O">Other</option>
            </select>
          </label>
          <Input label="Address" value={patient.address} onChange={pf("address")} className="col-span-2" />
          <Input label="City" value={patient.city} onChange={pf("city")} />
          <Input label="State" value={patient.state} onChange={pf("state")} />
          <Input label="ZIP" value={patient.zip} onChange={pf("zip")} />
          <Input label="Phone" value={patient.phone} onChange={pf("phone")} />
          <Input label="SSN" value={patient.ssn} onChange={pf("ssn")} />
        </div>
      </Section>

      {/* Insurance */}
      <Section title="Insurance Information">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Input label="Payer Name" value={insurance.payer_name} onChange={inf("payer_name")} required className="col-span-2" />
          <Input label="Payer ID" value={insurance.payer_id} onChange={inf("payer_id")} required />
          <label className="block">
            <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Plan Type *</span>
            <select
              value={insurance.plan_type}
              onChange={(e) => setInsurance((p) => ({ ...p, plan_type: e.target.value as InsuranceInfo["plan_type"] }))}
              className="mt-1 w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
            >
              <option value="Medicare">Medicare</option>
              <option value="Medicaid">Medicaid</option>
              <option value="Commercial">Commercial</option>
              <option value="Other">Other</option>
            </select>
          </label>
          <Input label="Member ID" value={insurance.member_id} onChange={inf("member_id")} required />
          <Input label="Group Number" value={insurance.group_number} onChange={inf("group_number")} />
        </div>
      </Section>

      {/* Provider */}
      <Section title="Provider / Facility">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Input label="Provider Name" value={provider.name} onChange={prf("name")} required className="col-span-2" />
          <Input label="NPI" value={provider.npi} onChange={prf("npi")} required />
          <Input label="Tax ID" value={provider.tax_id} onChange={prf("tax_id")} />
          <Input label="Address" value={provider.address} onChange={prf("address")} className="col-span-2" />
          <Input label="City" value={provider.city} onChange={prf("city")} />
          <Input label="State" value={provider.state} onChange={prf("state")} />
          <Input label="ZIP" value={provider.zip} onChange={prf("zip")} />
          <Input label="Phone" value={provider.phone} onChange={prf("phone")} />
        </div>
      </Section>

      {/* Service Details */}
      <Section title="Service Details">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Input label="Date of Service" type="date" value={dateOfService} onChange={setDateOfService} required />
          <Input label="Place of Service" value={placeOfService} onChange={setPlaceOfService} placeholder="11" />
          <Input label="CPT Codes" value={cptCodes} onChange={setCptCodes} placeholder="99213, 99214" className="col-span-2" />
          <Input label="Total Charge ($)" type="number" value={totalCharge} onChange={setTotalCharge} placeholder="0.00" />
          <Input label="Authorization #" value={authNumber} onChange={setAuthNumber} />
        </div>

        <div className="mt-4 pt-4 border-t border-gray-200 border-dashed">
          <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">ICD-10 Codes (from analysis)</span>
          <div className="flex flex-wrap gap-2 mt-2">
            {icdCodes.map((c) => (
              <span
                key={c}
                className="text-[11px] font-bold tracking-widest bg-brand-50 text-brand-700 px-2.5 py-1 rounded-md border border-brand-100 shadow-sm"
              >
                {c}
              </span>
            ))}
            {icdCodes.length === 0 && (
              <span className="text-xs text-brand-500 font-medium italic bg-brand-50 px-3 py-1 rounded-md">
                Run an analysis first to auto-populate ICD codes
              </span>
            )}
          </div>
        </div>
      </Section>

      <button
        type="submit"
        disabled={isLoading || icdCodes.length === 0}
        className="w-full py-3.5 mt-2 bg-brand-600 text-white rounded-full font-bold text-sm shadow-soft hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
      >
        {isLoading ? "Verifying Claim Data..." : "Submit Claim for Verification"}
      </button>
    </form>
  );
}
