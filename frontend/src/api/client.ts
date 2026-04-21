import type {
  ClinicalAnalysisResponse,
  CostEstimate,
  ClaimVerification,
  InsuranceClaim,
  SSEEvent,
} from "./types";

const BASE = "/api/v1";

/* ── Standard analyze (non-streaming) ── */

export async function analyzeNote(
  noteText: string,
  images: string[] = [],
): Promise<ClinicalAnalysisResponse> {
  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      note_text: noteText,
      images,
      include_report: true,
    }),
  });
  if (!res.ok) throw new Error(`Analyze failed: ${res.status}`);
  return res.json();
}

/* ── Streaming analyze (SSE via fetch ReadableStream) ── */

export async function analyzeStream(
  noteText: string,
  images: string[],
  onEvent: (evt: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE}/analyze/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      note_text: noteText,
      images,
      include_report: true,
    }),
    signal,
  });

  if (!res.ok) throw new Error(`Stream failed: ${res.status}`);
  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Parse SSE lines
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = "message";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6));
          onEvent({ event: currentEvent, data });
        } catch {
          // skip malformed lines
        }
      }
    }
  }
}

/* ── Image upload + analyze ── */

export async function analyzeWithImages(
  noteText: string,
  files: File[],
): Promise<ClinicalAnalysisResponse> {
  const form = new FormData();
  form.append("note_text", noteText);
  for (const f of files) form.append("images", f);
  const res = await fetch(`${BASE}/analyze/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

/* ── Billing endpoints ── */

export async function estimateCosts(
  icdCodes: string[],
): Promise<CostEstimate[]> {
  const res = await fetch(`${BASE}/billing/estimate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ icd_codes: icdCodes }),
  });
  if (!res.ok) throw new Error(`Estimate failed: ${res.status}`);
  return res.json();
}

export async function verifyClaim(
  claim: InsuranceClaim,
): Promise<ClaimVerification> {
  const res = await fetch(`${BASE}/billing/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(claim),
  });
  if (!res.ok) throw new Error(`Verify failed: ${res.status}`);
  return res.json();
}
