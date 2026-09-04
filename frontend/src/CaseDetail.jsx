import { useEffect, useState } from "react";
import { getCase, getCaseAudioUrl, postReview } from "./api.js";
import Waveform from "./Waveform.jsx";

function RiskGauge({ score, action }) {
  const pct = score == null ? 0 : Math.round(score * 100);
  const color = action === "block_and_review" ? "#e0645a" : action === "step_up" ? "#e0c34a" : "#59d67c";
  return (
    <div style={{ textAlign: "center" }}>
      <svg width="120" height="70" viewBox="0 0 120 70">
        <path d="M10,60 A50,50 0 0,1 110,60" fill="none" stroke="#262a33" strokeWidth="10" />
        <path
          d="M10,60 A50,50 0 0,1 110,60"
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeDasharray={`${(pct / 100) * 157} 157`}
        />
      </svg>
      <div style={{ fontSize: 24, fontWeight: 700 }}>{score == null ? "n/a" : pct + "%"}</div>
      <div className={`badge ${action}`}>{action}</div>
    </div>
  );
}

function SignalCard({ name, signal }) {
  if (!signal) return null;
  return (
    <div className="signal-card">
      <div className="name">{name}</div>
      <div className="score">{signal.score == null ? "—" : signal.score.toFixed(3)}</div>
      <div className="reason">{signal.reason}</div>
    </div>
  );
}

export default function CaseDetail({ caseId, onReviewed }) {
  const [data, setData] = useState(null);
  const [note, setNote] = useState("");

  useEffect(() => {
    if (caseId == null) return;
    getCase(caseId).then((d) => {
      setData(d);
      setNote(d?.case_note || "");
    });
  }, [caseId]);

  if (caseId == null) return <div className="detail-empty">Select a case from the queue.</div>;
  if (!data) return <div className="detail-empty">Loading…</div>;

  async function handleReview(action) {
    const updated = await postReview(caseId, action, note);
    setData(updated);
    onReviewed?.();
  }

  return (
    <div className="detail">
      <h2>Call {data.call_id}</h2>
      <div className="meta">{data.timestamp} · claimed channel: {data.claimed_channel}</div>

      <div className="gauge-row">
        <RiskGauge score={data.fused_score} action={data.action} />
        <div>
          <div><strong>Reason:</strong> {data.reason}</div>
          {data.degraded && <div style={{ color: "#e0c34a" }}>Degraded: {data.degradation_reasons.join("; ")}</div>}
        </div>
      </div>

      <Waveform audioUrl={getCaseAudioUrl(caseId)} timeline={data.spoof_timeline} />

      <div className="signal-cards">
        <SignalCard name="Spoof" signal={data.signals.spoof} />
        <SignalCard name="Channel" signal={data.signals.channel} />
        <SignalCard name="Voiceprint" signal={data.signals.voiceprint} />
        <SignalCard name="Intent" signal={data.signals.intent} />
      </div>

      <textarea
        className="case-note"
        placeholder="Case note…"
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />

      <div className="actions">
        <button onClick={() => handleReview(data.action)}>Accept</button>
        <button onClick={() => handleReview("step_up")}>Trigger step-up</button>
        <button onClick={() => handleReview(data.action === "block_and_review" ? "allow" : "block_and_review")}>
          Override
        </button>
      </div>

      {data.analyst_override && (
        <div className="meta" style={{ marginTop: 12 }}>
          Reviewed: {data.analyst_override} at {data.reviewed_at}
        </div>
      )}
    </div>
  );
}
