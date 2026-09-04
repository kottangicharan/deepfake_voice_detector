import { useState, useCallback } from "react";
import { AnimatePresence } from "motion/react";
import UploadView from "./UploadView.jsx";
import AnalyzingView from "./AnalyzingView.jsx";
import ResultView from "./ResultView.jsx";
import LiveMicView from "./LiveMicView.jsx";
import AdminView from "./AdminView.jsx";

/**
 * View state machine:
 *   upload ──┬── analyzing ──→ result ──→ admin
 *            └── mic ─────────→ result       │
 *              ↑                              │
 *              └──────── (reset) ─────────────┘
 */
export default function App() {
  const [view, setView] = useState("upload");
  const [result, setResult] = useState(null);
  const [analyzeFile, setAnalyzeFile] = useState(null);

  const handleFileSelected = useCallback((file) => {
    setAnalyzeFile(file);
    setView("analyzing");
  }, []);

  const handleMicStart = useCallback(() => setView("mic"), []);

  const handleAnalysisComplete = useCallback((data) => {
    setResult(data);
    setView("result");
  }, []);

  const handleReset = useCallback(() => {
    setResult(null);
    setAnalyzeFile(null);
    setView("upload");
  }, []);

  const handleShowAdmin = useCallback(() => setView("admin"), []);

  return (
    <div className="min-h-screen bg-bg">
      <AnimatePresence mode="wait">
        {view === "upload" && (
          <UploadView
            key="upload"
            onFileSelected={handleFileSelected}
            onMicStart={handleMicStart}
          />
        )}
        {view === "mic" && (
          <LiveMicView
            key="mic"
            onComplete={handleAnalysisComplete}
            onBack={handleReset}
          />
        )}
        {view === "analyzing" && (
          <AnalyzingView
            key="analyzing"
            file={analyzeFile}
            onComplete={handleAnalysisComplete}
            onError={handleReset}
          />
        )}
        {view === "result" && (
          <ResultView
            key="result"
            result={result}
            onReset={handleReset}
            onShowAdmin={handleShowAdmin}
          />
        )}
        {view === "admin" && (
          <AdminView key="admin" onBack={handleReset} />
        )}
      </AnimatePresence>
    </div>
  );
}
