export default function CaseQueue({ cases, selectedId, onSelect }) {
  return (
    <div className="queue">
      {cases.map((c) => (
        <div
          key={c.id}
          className={"queue-item" + (c.id === selectedId ? " selected" : "")}
          onClick={() => onSelect(c.id)}
        >
          <div>
            call {c.call_id.slice(0, 8)} <span className={`badge ${c.action}`}>{c.action}</span>
          </div>
          <div className="meta">
            {c.claimed_channel} · fused {c.fused_score != null ? c.fused_score.toFixed(2) : "n/a"}
            {c.abstain ? " · abstain" : ""}
          </div>
        </div>
      ))}
      {cases.length === 0 && <div className="meta" style={{ padding: 16 }}>No cases yet.</div>}
    </div>
  );
}
