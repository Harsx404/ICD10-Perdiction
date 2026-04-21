import React, { createContext, useContext, useReducer } from "react";
import type {
  ClinicalAnalysisResponse,
  StageState,
  AnalysisHistoryEntry,
} from "../api/types";

/* ── State shape ── */

interface AnalysisState {
  noteText: string;
  images: File[];
  imagePreviews: string[];
  isAnalyzing: boolean;
  error: string | null;
  stages: StageState[];
  result: ClinicalAnalysisResponse | null;
  history: AnalysisHistoryEntry[];
}

const DEFAULT_STAGES: StageState[] = [
  { id: "understanding", label: "Clinical Understanding", model: "Gemma 4", status: "idle", substeps: [] },
  { id: "icd-prediction", label: "ICD-10 Prediction", model: "FAISS + BioGPT", status: "idle", substeps: [] },
  { id: "rule-engine", label: "Rule Engine", model: "Deterministic", status: "idle", substeps: [] },
  { id: "icd-judge", label: "ICD Judge", model: "Gemma 4", status: "idle", substeps: [] },
  { id: "report", label: "Report Generation", model: "Gemma 4", status: "idle", substeps: [] },
];

function loadHistory(): AnalysisHistoryEntry[] {
  try {
    return JSON.parse(localStorage.getItem("analysis_history") || "[]");
  } catch {
    return [];
  }
}

const initialState: AnalysisState = {
  noteText: "",
  images: [],
  imagePreviews: [],
  isAnalyzing: false,
  error: null,
  stages: DEFAULT_STAGES,
  result: null,
  history: loadHistory(),
};

/* ── Actions ── */

type Action =
  | { type: "SET_NOTE"; text: string }
  | { type: "ADD_IMAGES"; files: File[]; previews: string[] }
  | { type: "REMOVE_IMAGE"; index: number }
  | { type: "START_ANALYSIS" }
  | { type: "STAGE_UPDATE"; stageId: string; status: StageState["status"]; detail?: string; elapsed?: number; substep?: string }
  | { type: "ANALYSIS_COMPLETE"; result: ClinicalAnalysisResponse }
  | { type: "ANALYSIS_ERROR"; error: string }
  | { type: "SET_DOC_ID"; doc_id: string }
  | { type: "RESET" }
  | { type: "LOAD_HISTORY_ENTRY"; entry: AnalysisHistoryEntry }
  | { type: "CLEAR_HISTORY" };

function reducer(state: AnalysisState, action: Action): AnalysisState {
  switch (action.type) {
    case "SET_NOTE":
      return { ...state, noteText: action.text };

    case "ADD_IMAGES":
      return {
        ...state,
        images: [...state.images, ...action.files],
        imagePreviews: [...state.imagePreviews, ...action.previews],
      };

    case "REMOVE_IMAGE": {
      const images = state.images.filter((_, i) => i !== action.index);
      const imagePreviews = state.imagePreviews.filter((_, i) => i !== action.index);
      return { ...state, images, imagePreviews };
    }

    case "START_ANALYSIS":
      return {
        ...state,
        isAnalyzing: true,
        error: null,
        result: null,
        stages: DEFAULT_STAGES.map((s) => ({ ...s, status: "idle" as const, substeps: [] })),
      };

    case "STAGE_UPDATE":
      return {
        ...state,
        stages: state.stages.map((s) =>
          s.id === action.stageId
            ? {
                ...s,
                status: action.status,
                detail: action.detail ?? s.detail,
                elapsed: action.elapsed ?? s.elapsed,
                substeps: action.substep ? [...s.substeps, action.substep] : s.substeps,
              }
            : s,
        ),
      };

    case "ANALYSIS_COMPLETE": {
      const entry: AnalysisHistoryEntry = {
        id: crypto.randomUUID(),
        timestamp: new Date().toISOString(),
        note_preview: state.noteText.slice(0, 120),
        note_text: state.noteText,
        response: action.result,
      };
      const history = [entry, ...state.history].slice(0, 50);
      localStorage.setItem("analysis_history", JSON.stringify(history));
      return { ...state, isAnalyzing: false, result: action.result, history };
    }

    case "ANALYSIS_ERROR":
      return { ...state, isAnalyzing: false, error: action.error };

    case "SET_DOC_ID":
      if (!state.result) return state;
      return { ...state, result: { ...state.result, doc_id: action.doc_id } };

    case "RESET":
      return { ...initialState, history: state.history };

    case "LOAD_HISTORY_ENTRY":
      return {
        ...state,
        noteText: action.entry.note_text,
        result: action.entry.response,
        isAnalyzing: false,
        error: null,
        stages: DEFAULT_STAGES,
      };

    case "CLEAR_HISTORY":
      localStorage.removeItem("analysis_history");
      return { ...state, history: [] };

    default:
      return state;
  }
}

/* ── Context ── */

const AnalysisStateCtx = createContext<AnalysisState>(initialState);
const AnalysisDispatchCtx = createContext<React.Dispatch<Action>>(() => {});

export function AnalysisProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <AnalysisStateCtx.Provider value={state}>
      <AnalysisDispatchCtx.Provider value={dispatch}>
        {children}
      </AnalysisDispatchCtx.Provider>
    </AnalysisStateCtx.Provider>
  );
}

export function useAnalysisState() {
  return useContext(AnalysisStateCtx);
}

export function useAnalysisDispatch() {
  return useContext(AnalysisDispatchCtx);
}
