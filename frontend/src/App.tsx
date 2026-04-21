import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout/Layout";
import AnalysisInputPage from "./pages/AnalysisInputPage";
import AnalysisProcessingPage from "./pages/AnalysisProcessingPage";
import AnalysisResultsPage from "./pages/AnalysisResultsPage";
import BillingPage from "./pages/BillingPage";
import HistoryPage from "./pages/HistoryPage";
import ReportPage from "./pages/ReportPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/analysis/input" replace />} />
        <Route path="/analysis" element={<Navigate to="/analysis/input" replace />} />
        <Route path="/analysis/input" element={<AnalysisInputPage />} />
        <Route path="/analysis/processing" element={<AnalysisProcessingPage />} />
        <Route path="/analysis/results" element={<AnalysisResultsPage />} />
        <Route path="/billing" element={<BillingPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/report" element={<ReportPage />} />
      </Route>
    </Routes>
  );
}
