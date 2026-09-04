import { motion } from "motion/react";
import {
  ShieldCheck,
  ShieldWarning,
  Warning,
  ArrowCounterClockwise,
  ArrowRight,
  Waveform as WaveformIcon,
} from "@phosphor-icons/react";
import Waveform from "./Waveform.jsx";
import { getCaseAudioUrl } from "./api.js";

/* ---- verdict presets ---- */
const verdicts = {
  allow: {
    icon: ShieldCheck,
    title: "Voice Verified",
    subtitle: "No signs of synthetic or cloned audio detected.",
    bg: "bg-emerald-500/10 border-emerald-500/20",
    text: "text-emerald-400",
    hex: "#34d399",
  },
  step_up: {
    icon: Warning,
    title: "Additional Verification Needed",
    subtitle: "Some signals require further review before proceeding.",
    bg: "bg-amber-500/10 border-amber-500/20",
    text: "text-amber-400",
    hex: "#fbbf24",
  },
  block_and_review: {
    icon: ShieldWarning,
    title: "Flagged for Review",
    subtitle: "This voice sample has been flagged for manual review.",
    bg: "bg-red-500/10 border-red-500/20",
    text: "text-red-400",
    hex: "#f87171",
  },
};

/* ---- human-readable signal names ---- */
const signalMeta = {
  spoof: { name: "Voice Authenticity", fallback: "Synthetic speech detection" },
  channel: { name: "Call Quality", fallback: "Audio channel analysis" },
  voiceprint: { name: "Voice Match", fallback: "Identity verification" },
};

function confidence(score) {
  if (score == null) return null;
  return Math.round((1 - score) * 100);
}

function levelColor(pct) {
  if (pct >= 80) return { label: "Strong", bar: "bg-emerald-500", text: "text-emerald-400" };
  if (pct >= 50) return { label: "Moderate", bar: "bg-amber-500", text: "text-amber-400" };
  return { label: "Weak", bar: "bg-red-500", text: "text-red-400" };
}

/* ---- signal card ---- */
function SignalCard({ signalKey, signal, delay }) {
  const meta = signalMeta[signalKey] || { name: signalKey, fallback: "" };
  const pct = confidence(signal?.score);
  const level = pct != null ? levelColor(pct) : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className="bg-surface rounded-xl border border-edge p-5"
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-subtle text-xs font-medium uppercase tracking-wider">
          {meta.name}
        </span>
        {level ? (
          <span className={`text-xs font-semibold ${level.text}`}>{level.label}</span>
        ) : (
          <span className="text-xs text-muted">N/A</span>
        )}
      </div>

      <div className="w-full h-2 bg-raised rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct ?? 0}%` }}
          transition={{ duration: 0.8, ease: "easeOut", delay: delay + 0.1 }}
          className={`h-full rounded-full ${level?.bar ?? "bg-muted"}`}
        />
      </div>

      <p className="text-muted text-xs mt-2.5 leading-relaxed">
        {signal?.reason || meta.fallback}
      </p>
    </motion.div>
  );
}

/* ---- result view ---- */
export default function ResultView({ result, onReset, onShowAdmin }) {
  if (!result) return null;

  const v = verdicts[result.action] || verdicts.step_up;
  const Icon = v.icon;
  const signals = result.signals || {};
  const fusedConf = confidence(result.fused_score);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen"
    >
      {/* nav */}
      <nav className="flex items-center px-6 md:px-10 h-16 border-b border-edge/50">
        <WaveformIcon size={24} weight="bold" className="text-blue-500" />
        <span className="ml-2.5 text-[15px] font-semibold tracking-tight text-white">
          VoiceGuard
        </span>
      </nav>

      <div className="max-w-3xl mx-auto px-6 md:px-10 py-12 md:py-20">
        {/* ---- verdict card ---- */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className={`rounded-2xl border p-8 md:p-10 text-center ${v.bg}`}
        >
          <Icon size={56} weight="duotone" color={v.hex} className="mx-auto mb-4" />
          <h1 className={`text-2xl md:text-3xl font-bold tracking-tight ${v.text}`}>
            {v.title}
          </h1>
          <p className="text-subtle mt-2 text-sm max-w-[50ch] mx-auto">
            {v.subtitle}
          </p>
          {fusedConf != null && (
            <p className="mt-4 text-muted text-xs">
              Confidence score: {fusedConf}%
            </p>
          )}
        </motion.div>

        {/* ---- signal breakdown ---- */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.25 }}
          className="mt-10"
        >
          <h2 className="text-white font-semibold text-[15px] mb-4">
            Analysis Breakdown
          </h2>
          <div className="grid sm:grid-cols-3 gap-3">
            {["spoof", "channel", "voiceprint"].map((key, i) => (
              <SignalCard
                key={key}
                signalKey={key}
                signal={signals[key]}
                delay={0.3 + i * 0.08}
              />
            ))}
          </div>
        </motion.div>

        {/* ---- waveform ---- */}
        {result.case_id && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="mt-10"
          >
            <h2 className="text-white font-semibold text-[15px] mb-4">
              Audio Waveform
            </h2>
            <Waveform
              audioUrl={getCaseAudioUrl(result.case_id)}
              timeline={result.spoof_timeline}
            />
          </motion.div>
        )}

        {/* ---- degradation banner ---- */}
        {result.degraded && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.55 }}
            className="mt-6 p-4 rounded-xl bg-amber-500/[0.06] border border-amber-500/15
                       text-amber-400 text-xs leading-relaxed"
          >
            <strong>Degraded analysis:</strong>{" "}
            {Array.isArray(result.degradation_reasons)
              ? result.degradation_reasons.join("; ")
              : "Some signals were unavailable"}
          </motion.div>
        )}

        {/* ---- actions ---- */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="mt-10 flex flex-wrap gap-3"
        >
          <button
            onClick={onReset}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl
                       bg-raised border border-edge hover:bg-edge/60 text-white
                       text-sm font-medium transition-colors cursor-pointer"
          >
            <ArrowCounterClockwise size={18} />
            Try Another
          </button>
          <button
            onClick={onShowAdmin}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl
                       text-subtle hover:text-white text-sm font-medium
                       transition-colors cursor-pointer"
          >
            View Full Analysis
            <ArrowRight size={18} />
          </button>
        </motion.div>
      </div>
    </motion.div>
  );
}
