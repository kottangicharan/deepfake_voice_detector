import { useCallback, useRef, useState } from "react";
import { motion } from "motion/react";
import {
  Microphone,
  UploadSimple,
  ShieldCheck,
  Lightning,
  LockSimple,
  Waveform,
} from "@phosphor-icons/react";

/* ---- animated hero waveform ---- */
function WaveAnimation() {
  return (
    <div className="flex items-end justify-center gap-[3px] h-48">
      {Array.from({ length: 32 }).map((_, i) => (
        <motion.div
          key={i}
          className="w-1.5 rounded-full bg-blue-500/30"
          animate={{
            height: [
              20 + Math.sin(i * 0.5) * 30,
              50 + Math.cos(i * 0.3) * 80,
              20 + Math.sin(i * 0.5) * 30,
            ],
          }}
          transition={{
            duration: 1.4 + (i % 5) * 0.15,
            repeat: Infinity,
            repeatType: "reverse",
            ease: "easeInOut",
            delay: i * 0.04,
          }}
        />
      ))}
    </div>
  );
}

const features = [
  {
    icon: ShieldCheck,
    title: "Real-time Analysis",
    desc: "AI-powered voice pattern verification in seconds",
  },
  {
    icon: Lightning,
    title: "Instant Results",
    desc: "Get a clear verdict immediately after upload",
  },
  {
    icon: LockSimple,
    title: "Privacy First",
    desc: "Audio is processed securely and never shared",
  },
];

export default function UploadView({ onFileSelected, onMicStart }) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) onFileSelected(file);
    },
    [onFileSelected]
  );

  const handleFileChange = useCallback(
    (e) => {
      const file = e.target.files[0];
      if (file) onFileSelected(file);
    },
    [onFileSelected]
  );

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen"
    >
      {/* ---- nav ---- */}
      <nav className="flex items-center px-6 md:px-10 h-16 border-b border-edge/50">
        <Waveform size={24} weight="bold" className="text-blue-500" />
        <span className="ml-2.5 text-[15px] font-semibold tracking-tight text-white">
          VoiceGuard
        </span>
      </nav>

      {/* ---- hero ---- */}
      <div className="max-w-6xl mx-auto px-6 md:px-10 pt-20 md:pt-32 pb-16">
        <div className="grid md:grid-cols-[1.2fr_1fr] gap-16 items-center">
          {/* left */}
          <div>
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="text-4xl md:text-6xl font-bold tracking-tighter leading-[1.05] text-white"
            >
              Voice
              <br />
              Authentication
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="mt-5 text-base md:text-lg text-subtle leading-relaxed max-w-[45ch]"
            >
              Verify your identity instantly with advanced
              AI&#8209;powered voice analysis.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="flex flex-wrap gap-3 mt-8"
            >
              <button
                onClick={onMicStart}
                className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl
                           bg-blue-600 hover:bg-blue-500 text-white font-medium
                           text-[15px] transition-colors cursor-pointer"
              >
                <Microphone size={20} weight="bold" />
                Use Microphone
              </button>
              <button
                onClick={() => inputRef.current?.click()}
                className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl
                           bg-raised border border-edge hover:bg-edge/60 text-white
                           font-medium text-[15px] transition-colors cursor-pointer"
              >
                <UploadSimple size={20} weight="bold" />
                Upload File
              </button>
              <input
                ref={inputRef}
                type="file"
                accept="audio/*"
                onChange={handleFileChange}
                className="hidden"
              />
            </motion.div>
          </div>

          {/* right — animated waveform */}
          <motion.div
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="hidden md:flex items-center justify-center"
          >
            <div
              className="relative w-full aspect-square max-w-[340px]
                          flex items-center justify-center"
            >
              <div className="absolute inset-0 bg-blue-500/[0.04] rounded-3xl border border-blue-500/10" />
              <WaveAnimation />
            </div>
          </motion.div>
        </div>

        {/* ---- drop zone ---- */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className={`mt-16 border-2 border-dashed rounded-2xl py-10 text-center
                      transition-colors cursor-pointer ${
                        dragOver
                          ? "border-blue-500 bg-blue-500/5"
                          : "border-edge hover:border-subtle/30"
                      }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <UploadSimple size={32} className="mx-auto text-muted mb-3" />
          <p className="text-subtle text-sm">
            Drag and drop an audio file here, or{" "}
            <span className="text-blue-400 underline underline-offset-2">
              browse
            </span>
          </p>
          <p className="text-muted text-xs mt-1">
            .wav, .mp3, .flac — up to 50 MB
          </p>
        </motion.div>

        {/* ---- features ---- */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="grid md:grid-cols-3 gap-4 mt-16"
        >
          {features.map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="bg-surface rounded-2xl border border-edge p-6"
            >
              <Icon size={28} weight="duotone" className="text-blue-400 mb-3" />
              <h3 className="text-white font-semibold text-[15px] mb-1">
                {title}
              </h3>
              <p className="text-subtle text-sm leading-relaxed">{desc}</p>
            </div>
          ))}
        </motion.div>
      </div>
    </motion.div>
  );
}
