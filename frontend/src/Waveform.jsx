import { useEffect, useRef } from "react";

// green (low risk) -> red (high risk)
function colorFor(score) {
  const r = Math.round(255 * score);
  const g = Math.round(255 * (1 - score));
  return `rgb(${r},${g},80)`;
}

export default function Waveform({ audioUrl, timeline }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!audioUrl) return;
    let cancelled = false;

    fetch(audioUrl)
      .then((r) => r.arrayBuffer())
      .then((buf) => new (window.AudioContext || window.webkitAudioContext)().decodeAudioData(buf))
      .then((audioBuffer) => {
        if (cancelled) return;
        draw(audioBuffer);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [audioUrl, timeline]);

  function draw(audioBuffer) {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    const data = audioBuffer.getChannelData(0);
    const duration = audioBuffer.duration;
    const samplesPerPixel = Math.max(1, Math.floor(data.length / width));

    for (let x = 0; x < width; x++) {
      let min = 1, max = -1;
      const start = x * samplesPerPixel;
      for (let i = 0; i < samplesPerPixel; i++) {
        const v = data[start + i] || 0;
        if (v < min) min = v;
        if (v > max) max = v;
      }
      const t = (x / width) * duration;
      const score = scoreAtTime(t);
      ctx.strokeStyle = score == null ? "#4a5568" : colorFor(score);
      ctx.beginPath();
      ctx.moveTo(x, ((1 + min) / 2) * height);
      ctx.lineTo(x, ((1 + max) / 2) * height);
      ctx.stroke();
    }
  }

  function scoreAtTime(t) {
    if (!timeline) return null;
    const window = timeline.find(([start, end]) => t >= start && t < end);
    return window ? window[2] : null;
  }

  return <canvas ref={canvasRef} width={640} height={100} style={{ width: "100%", background: "#171a21", borderRadius: 6 }} />;
}
