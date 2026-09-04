import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { ArrowLeft, Waveform as WaveformIcon } from "@phosphor-icons/react";
import CaseQueue from "./CaseQueue.jsx";
import CaseDetail from "./CaseDetail.jsx";
import LiveCall from "./LiveCall.jsx";
import { getCases } from "./api.js";

export default function AdminView({ onBack }) {
  const [cases, setCases] = useState([]);
  const [selectedId, setSelectedId] = useState(null);

  async function refresh() {
    try {
      const data = await getCases();
      setCases(data?.cases || []);
    } catch (e) {
      console.error("Failed to load cases:", e);
    }
  }

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="h-screen flex flex-col"
    >
      {/* nav */}
      <nav className="flex items-center justify-between px-6 md:px-10 h-16 border-b border-edge/50 shrink-0">
        <div className="flex items-center gap-2.5">
          <WaveformIcon size={24} weight="bold" className="text-blue-500" />
          <span className="text-[15px] font-semibold tracking-tight text-white">
            VoiceGuard
          </span>
          <span className="text-xs text-muted bg-raised px-2 py-0.5 rounded-md ml-2">
            Analyst Console
          </span>
        </div>
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-subtle hover:text-white
                     text-sm transition-colors cursor-pointer"
        >
          <ArrowLeft size={16} />
          Back to Home
        </button>
      </nav>

      {/* legacy two-panel layout — uses the old CSS classes */}
      <div className="flex-1 grid grid-cols-[320px_1fr] min-h-0">
        <CaseQueue cases={cases} selectedId={selectedId} onSelect={setSelectedId} />
        <div className="overflow-y-auto">
          <CaseDetail caseId={selectedId} onReviewed={refresh} />
          <LiveCall claimedChannel="app" onCallEnded={refresh} />
        </div>
      </div>
    </motion.div>
  );
}
