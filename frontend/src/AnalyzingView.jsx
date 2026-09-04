import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { WarningCircle, ArrowCounterClockwise } from "@phosphor-icons/react";
import { postScore } from "./api.js";

const stages = [
  "Preparing audio…",
  "Analyzing voice patterns…",
  "Checking authenticity signals…",
  "Evaluating channel quality…",
  "Computing risk score…",
  "Finalizing results…",
];

export default function AnalyzingView({ file, onComplete, onError }) {
  const [stage, setStage] = useState(0);
  const [error, setError] = useState(null);

  /* cycle through progress messages */
  useEffect(() => {
    if (error) return;
    const id = setInterval(() => setStage((s) => (s + 1) % stages.length), 2200);
    return () => clearInterval(id);
  }, [error]);

  /* POST the file and transition to result */
  useEffect(() => {
    if (!file) return;
    let cancelled = false;

    postScore(file)
      .then((data) => {
        if (!cancelled) onComplete(data);
      })
      .catch((err) => {
        console.error("Score error:", err);
        if (!cancelled) {
          setError(
            err.message?.includes("500")
              ? "The backend returned an error. Make sure the API server is running on port 8123."
              : err.message?.includes("Failed to fetch") || err.message?.includes("NetworkError")
              ? "Cannot reach the backend. Start the API server first."
              : `Analysis failed: ${err.message}`
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [file, onComplete]);

  /* ---- error state ---- */
  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3 }}
        className="min-h-screen flex flex-col items-center justify-center px-6"
      >
        <div className="max-w-md text-center">
          <WarningCircle size={56} weight="duotone" className="text-red-400 mx-auto mb-5" />
          <h2 className="text-white text-xl font-bold tracking-tight mb-2">
            Something went wrong
          </h2>
          <p className="text-subtle text-sm leading-relaxed mb-8">{error}</p>
          <button
            onClick={onError}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl
                       bg-raised border border-edge hover:bg-edge/60 text-white
                       text-sm font-medium transition-colors cursor-pointer"
          >
            <ArrowCounterClockwise size={18} />
            Try Again
          </button>
        </div>
      </motion.div>
    );
  }

  /* ---- analyzing animation ---- */
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen flex flex-col items-center justify-center px-6"
    >
      {/* pulsing concentric rings */}
      <div className="relative w-36 h-36 mb-12">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="absolute inset-0 rounded-full border-2 border-blue-500/25"
            animate={{ scale: [1, 1.6 + i * 0.35], opacity: [0.5, 0] }}
            transition={{
              duration: 2.2,
              repeat: Infinity,
              delay: i * 0.55,
              ease: "easeOut",
            }}
          />
        ))}
        <div className="absolute inset-0 flex items-center justify-center">
          <div
            className="w-16 h-16 rounded-full bg-blue-500/10 border border-blue-500/20
                        flex items-center justify-center"
          >
            <motion.div
              className="w-6 h-6 rounded-full bg-blue-500"
              animate={{ scale: [1, 1.25, 1] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
            />
          </div>
        </div>
      </div>

      {/* rotating status text */}
      <AnimatePresence mode="wait">
        <motion.p
          key={stage}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.25 }}
          className="text-white text-lg font-medium"
        >
          {stages[stage]}
        </motion.p>
      </AnimatePresence>

      <p className="text-muted text-sm mt-3">This usually takes a few seconds</p>
    </motion.div>
  );
}
