import { useRef, useState, useEffect, useCallback } from "react";
import { motion } from "motion/react";
import {
  Microphone,
  Stop,
  ArrowLeft,
  Waveform as WaveformIcon,
} from "@phosphor-icons/react";

const CHUNK_SAMPLES = 3200; // ~200 ms @ 16 kHz

function floatTo16BitPCM(float32) {
  const out = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function confidenceColor(pct) {
  if (pct >= 80) return { bar: "bg-emerald-500", text: "text-emerald-400" };
  if (pct >= 50) return { bar: "bg-amber-500", text: "text-amber-400" };
  return { bar: "bg-red-500", text: "text-red-400" };
}

export default function LiveMicView({ onComplete, onBack }) {
  const [state, setState] = useState("idle"); // idle | recording | processing
  const [update, setUpdate] = useState(null);
  const [error, setError] = useState(null);
  const [elapsed, setElapsed] = useState(0);

  const wsRef = useRef(null);
  const audioCtxRef = useRef(null);
  const streamRef = useRef(null);
  const pendingRef = useRef([]);
  const timerRef = useRef(null);
  const lastUpdateRef = useRef(null);

  /* ---- start recording ---- */
  const start = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioCtx = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 16000,
      });
      audioCtxRef.current = audioCtx;
      await audioCtx.audioWorklet.addModule("/pcm-worklet.js");

      const wsProto = location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${wsProto}://${location.host}/stream`);
      wsRef.current = ws;

      ws.onopen = () => ws.send(JSON.stringify({ claimed_channel: "app" }));
      ws.onmessage = (evt) => {
        const data = JSON.parse(evt.data);
        setUpdate(data);
        lastUpdateRef.current = data;
      };
      ws.onerror = () => setError("Connection error. Please try again.");
      ws.onclose = () => {
        /* when the socket closes, surface the last result */
        if (lastUpdateRef.current && state !== "idle") {
          onComplete(lastUpdateRef.current);
        }
      };

      const source = audioCtx.createMediaStreamSource(stream);
      const node = new AudioWorkletNode(audioCtx, "pcm-processor");
      node.port.onmessage = (evt) => {
        pendingRef.current.push(evt.data);
        const total = pendingRef.current.reduce((n, a) => n + a.length, 0);
        if (total >= CHUNK_SAMPLES && ws.readyState === WebSocket.OPEN) {
          const merged = new Float32Array(total);
          let off = 0;
          for (const arr of pendingRef.current) {
            merged.set(arr, off);
            off += arr.length;
          }
          pendingRef.current = [];
          ws.send(floatTo16BitPCM(merged).buffer);
        }
      };
      source.connect(node);

      setState("recording");
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    } catch {
      setError("Microphone access denied. Please allow microphone permissions.");
    }
  }, [onComplete, state]);

  /* ---- stop recording ---- */
  function stop() {
    setState("processing");
    clearInterval(timerRef.current);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "end_call" }));
    }
    wsRef.current?.close();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    audioCtxRef.current?.close();
  }

  /* cleanup on unmount */
  useEffect(() => {
    return () => {
      clearInterval(timerRef.current);
      wsRef.current?.close();
      streamRef.current?.getTracks().forEach((t) => t.stop());
      audioCtxRef.current?.close();
    };
  }, []);

  const score = update?.smoothed_score;
  const pct = score != null ? Math.round((1 - score) * 100) : null;
  const colors = pct != null ? confidenceColor(pct) : null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen"
    >
      {/* ---- nav ---- */}
      <nav className="flex items-center justify-between px-6 md:px-10 h-16 border-b border-edge/50">
        <div className="flex items-center gap-2.5">
          <WaveformIcon size={24} weight="bold" className="text-blue-500" />
          <span className="text-[15px] font-semibold tracking-tight text-white">
            VoiceGuard
          </span>
        </div>
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-subtle hover:text-white
                     text-sm transition-colors cursor-pointer"
        >
          <ArrowLeft size={16} />
          Back
        </button>
      </nav>

      <div className="max-w-lg mx-auto px-6 py-20 md:py-32 text-center">
        {/* ---- idle: tap-to-record ---- */}
        {state === "idle" && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white mb-3">
              Ready to Record
            </h1>
            <p className="text-subtle text-sm mb-10 max-w-[40ch] mx-auto">
              Tap the microphone and speak naturally for at least 3 seconds.
            </p>
            <button
              onClick={start}
              className="w-28 h-28 rounded-full bg-blue-600 hover:bg-blue-500
                         flex items-center justify-center mx-auto transition-colors cursor-pointer"
            >
              <Microphone size={40} weight="bold" className="text-white" />
            </button>
          </motion.div>
        )}

        {/* ---- recording ---- */}
        {state === "recording" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="relative w-32 h-32 mx-auto mb-8">
              <motion.div
                className="absolute inset-0 rounded-full bg-red-500/20"
                animate={{ scale: [1, 1.45, 1], opacity: [0.4, 0.08, 0.4] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              />
              <button
                onClick={stop}
                className="absolute inset-0 w-full h-full rounded-full bg-red-600
                           hover:bg-red-500 flex items-center justify-center
                           transition-colors cursor-pointer"
              >
                <Stop size={36} weight="fill" className="text-white" />
              </button>
            </div>

            <p className="text-white text-lg font-medium">Listening…</p>
            <p className="text-muted text-sm mt-1">{formatTime(elapsed)} elapsed</p>

            {/* live confidence card */}
            {pct != null && colors && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-8 bg-surface rounded-xl border border-edge p-6 max-w-xs mx-auto"
              >
                <p className="text-subtle text-xs font-medium uppercase tracking-wider mb-2">
                  Real-time Confidence
                </p>
                <p className={`text-4xl font-bold tracking-tight ${colors.text}`}>
                  {pct}%
                </p>
                <div className="w-full h-2 bg-raised rounded-full overflow-hidden mt-3">
                  <motion.div
                    className={`h-full rounded-full ${colors.bar}`}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </motion.div>
            )}
          </motion.div>
        )}

        {/* ---- processing spinner ---- */}
        {state === "processing" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="relative w-20 h-20 mx-auto mb-6">
              <motion.div
                className="absolute inset-0 rounded-full border-2 border-blue-500/30"
                animate={{ rotate: 360 }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
              >
                <div className="w-2.5 h-2.5 rounded-full bg-blue-500 absolute -top-1.5 left-1/2 -translate-x-1/2" />
              </motion.div>
            </div>
            <p className="text-white text-lg font-medium">Processing…</p>
          </motion.div>
        )}

        {/* ---- error ---- */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8 p-4 rounded-xl bg-red-500/10 border border-red-500/20
                       text-red-400 text-sm"
          >
            {error}
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
