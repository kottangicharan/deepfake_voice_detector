import { useEffect, useRef } from "react";

/* green (safe) → red (risky) */
function colorFor(score) {
  const r = Math.round(255 * score);
  const g = Math.round(255 * (1 - score));
  return `rgb(${r},${g},80)`;
}

export default function Waveform({ audioUrl, timeline }) {
  const canvasRef = useRef(null);
  const ctxRef = useRef(null);

  useEffect(() => {
    if (!audioUrl) return;
    let cancelled = false;

    /* share a single AudioContext for decoding — close when done */
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

    fetch(audioUrl)
      .then((r) => {
        if (!r.ok) throw new Error(r.status);
        return r.arrayBuffer();
      })
      .then((buf) => audioCtx.decodeAudioData(buf))
      .then((audioBuffer) => {
        if (!cancelled) draw(audioBuffer);
      })
      .catch(() => {
        /* silently degrade — no waveform */
      })
      .finally(() => audioCtx.close());

    return () => {
      cancelled = true;
    };
  }, [audioUrl, timeline]);

  function draw(audioBuffer) {
    const canvas = canvasRef.current;
    if (!canvas) return;

    /* match canvas resolution to rendered size for crisp output */
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;

    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    ctxRef.current = ctx;

    const width = rect.width;
    const height = rect.height;
    ctx.clearRect(0, 0, width, height);

    const data = audioBuffer.getChannelData(0);
    const duration = audioBuffer.duration;
    const samplesPerPixel = Math.max(1, Math.floor(data.length / width));

    /* pre-sort timeline for binary-search lookup */
    const tl = timeline ? [...timeline].sort((a, b) => a[0] - b[0]) : null;

    for (let x = 0; x < width; x++) {
      let min = 1;
      let max = -1;
      const start = x * samplesPerPixel;
      for (let i = 0; i < samplesPerPixel; i++) {
        const v = data[start + i] || 0;
        if (v < min) min = v;
        if (v > max) max = v;
      }

      const t = (x / width) * duration;
      const score = scoreAtTime(t, tl);
      ctx.strokeStyle = score == null ? "#334155" : colorFor(score);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, ((1 + min) / 2) * height);
      ctx.lineTo(x, ((1 + max) / 2) * height);
      ctx.stroke();
    }
  }

  return (
    <canvas
      ref={canvasRef}
      style={{
        width: "100%",
        height: 100,
        background: "#0F1219",
        borderRadius: 12,
        border: "1px solid #1E2330",
      }}
    />
  );
}

/** Binary search the sorted timeline for the window containing time t. */
function scoreAtTime(t, tl) {
  if (!tl || tl.length === 0) return null;
  let lo = 0;
  let hi = tl.length - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >>> 1;
    const [start, end, score] = tl[mid];
    if (t < start) hi = mid - 1;
    else if (t >= end) lo = mid + 1;
    else return score;
  }
  return null;
}
