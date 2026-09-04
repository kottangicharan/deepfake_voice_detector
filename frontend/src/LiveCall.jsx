import { useRef, useState } from "react";

const CHUNK_SAMPLES = 3200; // ~200ms @ 16kHz

function floatTo16BitPCM(float32) {
  const out = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

export default function LiveCall({ claimedChannel, onCallEnded }) {
  const [active, setActive] = useState(false);
  const [update, setUpdate] = useState(null);
  const [error, setError] = useState(null);

  const wsRef = useRef(null);
  const audioCtxRef = useRef(null);
  const streamRef = useRef(null);
  const pendingRef = useRef([]);

  async function start() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      audioCtxRef.current = audioCtx;
      await audioCtx.audioWorklet.addModule("/pcm-worklet.js");

      const wsProto = window.location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${wsProto}://${window.location.host}/stream`);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ claimed_channel: claimedChannel }));
      };
      ws.onmessage = (evt) => setUpdate(JSON.parse(evt.data));
      ws.onerror = () => setError("WebSocket error");
      ws.onclose = () => onCallEnded?.();

      const source = audioCtx.createMediaStreamSource(stream);
      const node = new AudioWorkletNode(audioCtx, "pcm-processor");
      node.port.onmessage = (evt) => {
        pendingRef.current.push(evt.data);
        const total = pendingRef.current.reduce((n, a) => n + a.length, 0);
        if (total >= CHUNK_SAMPLES && ws.readyState === WebSocket.OPEN) {
          const merged = new Float32Array(total);
          let offset = 0;
          for (const arr of pendingRef.current) {
            merged.set(arr, offset);
            offset += arr.length;
          }
          pendingRef.current = [];
          ws.send(floatTo16BitPCM(merged).buffer);
        }
      };
      source.connect(node);

      setActive(true);
    } catch (e) {
      setError(String(e));
    }
  }

  function stop() {
    wsRef.current?.readyState === WebSocket.OPEN && wsRef.current.send(JSON.stringify({ type: "end_call" }));
    wsRef.current?.close();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    audioCtxRef.current?.close();
    setActive(false);
    setUpdate(null);
  }

  return (
    <div className="live-panel">
      <strong>Live Call</strong>
      {!active ? (
        <div style={{ marginTop: 8 }}>
          <button onClick={start}>Start call (mic)</button>
        </div>
      ) : (
        <div style={{ marginTop: 8 }}>
          <button onClick={stop}>End call</button>
          {update && (
            <>
              <div className="live-score">
                {update.smoothed_score != null ? (update.smoothed_score * 100).toFixed(0) + "%" : "…"}
              </div>
              <span className={`badge ${update.action}`}>{update.action}</span>
              {update.abstain && <span className="badge block_and_review" style={{ marginLeft: 8 }}>abstain</span>}
            </>
          )}
        </div>
      )}
      {error && <div style={{ color: "#e0645a", marginTop: 8 }}>{error}</div>}
    </div>
  );
}
