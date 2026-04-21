import { useCallback, useRef } from "react";
import { useAnalysisState, useAnalysisDispatch } from "../context/AnalysisContext";
import { analyzeStream, analyzeNote } from "../api/client";
import type { SSEEvent } from "../api/types";

export function useAnalysis() {
  const state = useAnalysisState();
  const dispatch = useAnalysisDispatch();
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(async () => {
    if (!state.noteText.trim() && state.images.length === 0) return;

    dispatch({ type: "START_ANALYSIS" });
    abortRef.current = new AbortController();

    // Convert images to base64 for SSE stream
    const imageB64: string[] = [];
    for (const file of state.images) {
      const buf = await file.arrayBuffer();
      const b64 = btoa(
        new Uint8Array(buf).reduce((s, b) => s + String.fromCharCode(b), ""),
      );
      imageB64.push(b64);
    }

    try {
      // Try streaming first
      let finalResult: Record<string, unknown> | null = null;
      let pendingDocId: string | null = null;

      await analyzeStream(
        state.noteText,
        imageB64,
        (evt: SSEEvent) => {
          switch (evt.event) {
            case "stage":
              dispatch({
                type: "STAGE_UPDATE",
                stageId: evt.data.id as string,
                status: evt.data.status as "running" | "complete" | "error",
                detail: evt.data.detail as string | undefined,
                elapsed: evt.data.elapsed as number | undefined,
                substep: evt.data.substep as string | undefined,
              });
              break;
            case "result":
              finalResult = evt.data;
              break;
            case "doc_id":
              pendingDocId = evt.data.doc_id as string;
              break;
            case "error":
              dispatch({ type: "ANALYSIS_ERROR", error: evt.data.message as string });
              break;
          }
        },
        abortRef.current.signal,
      );

      if (finalResult) {
        // Merge doc_id (arrives after result event) before storing result
        if (pendingDocId) {
          (finalResult as Record<string, unknown>).doc_id = pendingDocId;
        }
        dispatch({ type: "ANALYSIS_COMPLETE", result: finalResult as never });
      }
    } catch (err) {
      // Fallback to non-streaming if stream endpoint not available
      if (err instanceof Error && err.message.includes("404")) {
        try {
          const result = await analyzeNote(state.noteText, imageB64);
          // Mark all stages complete
          for (const id of ["understanding", "icd-prediction", "rule-engine", "icd-judge", "report"]) {
            dispatch({ type: "STAGE_UPDATE", stageId: id, status: "complete" });
          }
          dispatch({ type: "ANALYSIS_COMPLETE", result });
        } catch (fallbackErr) {
          dispatch({
            type: "ANALYSIS_ERROR",
            error: fallbackErr instanceof Error ? fallbackErr.message : "Analysis failed",
          });
        }
      } else if (err instanceof DOMException && err.name === "AbortError") {
        dispatch({ type: "ANALYSIS_ERROR", error: "Analysis cancelled" });
      } else {
        dispatch({
          type: "ANALYSIS_ERROR",
          error: err instanceof Error ? err.message : "Analysis failed",
        });
      }
    }
  }, [state.noteText, state.images, dispatch]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    dispatch({ type: "RESET" });
  }, [dispatch]);

  return { ...state, dispatch, run, cancel, reset };
}
