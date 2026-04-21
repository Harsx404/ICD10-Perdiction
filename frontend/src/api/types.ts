/* ── Domain types mirroring app/domain/schemas.py ── */

export interface ClinicalEntities {
  diseases: string[];
  symptoms: string[];
  severity: string[];
  negations: string[];
  complications: string[];
}

export interface IcdCode {
  code: string;
  description: string;
  confidence: number;
}

export interface PrimaryIcdCode {
  code: string;
  description: string;
  confidence: number;
  rationale: string;
}

export interface DiagnosisSuggestion {
  label: string;
  probability: number;
  rationale: string;
}

export interface RiskSignal {
  label: string;
  severity: "low" | "moderate" | "high";
  rationale: string;
}

export interface ClinicalAnalysisResponse {
  mode: "full" | "degraded";
  entities: ClinicalEntities;
  icd_codes: IcdCode[];
  primary_icd_code?: PrimaryIcdCode | null;
  diagnosis: DiagnosisSuggestion[];
  risks: RiskSignal[];
  report: string;
  validation_notes: string[];
  doc_id?: string | null;
}

/* ── Pipeline streaming events ── */

export type StageStatus = "idle" | "running" | "complete" | "error";

export interface StageState {
  id: string;
  label: string;
  model: string;
  status: StageStatus;
  elapsed?: number;
  detail?: string;
  substeps: string[];
}

export interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
}

/* ── Billing types ── */

export interface CostEstimate {
  code: string;
  description: string;
  estimated_cost_low: number;
  estimated_cost_high: number;
  drg_category: string;
}

export interface ClaimIssue {
  code: string;
  severity: "info" | "warning" | "error";
  message: string;
}

export interface ClaimVerification {
  status: "approved" | "flagged" | "denied";
  issues: ClaimIssue[];
  recommendations: string[];
}

export interface PatientInfo {
  name: string;
  dob: string;
  gender: "M" | "F" | "O";
  address: string;
  city: string;
  state: string;
  zip: string;
  phone: string;
  ssn: string;
}

export interface InsuranceInfo {
  payer_name: string;
  payer_id: string;
  member_id: string;
  group_number: string;
  plan_type: "Medicare" | "Medicaid" | "Commercial" | "Other";
}

export interface ProviderInfo {
  name: string;
  npi: string;
  tax_id: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  phone: string;
}

export interface InsuranceClaim {
  patient: PatientInfo;
  insurance: InsuranceInfo;
  provider: ProviderInfo;
  icd_codes: string[];
  cpt_codes: string[];
  date_of_service: string;
  place_of_service: string;
  total_charge: number;
  authorization_number?: string;
}

/* ── History ── */

export interface AnalysisHistoryEntry {
  id: string;
  timestamp: string;
  note_preview: string;
  note_text: string;
  images?: string[];
  response: ClinicalAnalysisResponse;
}
