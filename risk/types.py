"""The one decision shape fusion/policy/audit/api all share."""
from dataclasses import asdict, dataclass, field


@dataclass
class SignalResult:
    score: float | None  # None = signal not run / unavailable
    reason: str
    confidence: float = 0.0


@dataclass
class Decision:
    call_id: str
    timestamp: str  # ISO8601 UTC
    claimed_channel: str
    signals: dict[str, SignalResult]  # keys: "spoof", "channel", "voiceprint", "intent"
    fused_score: float | None  # None only for pre-fusion abstain (insufficient audio)
    fused_confidence: float
    action: str  # always "allow" | "step_up" | "block_and_review"
    abstain: bool  # orthogonal to action: "route to human"
    reason: str
    degraded: bool
    degradation_reasons: list[str]
    threshold_version: str
    model_versions: dict[str, str]
    spoof_timeline: list[tuple[float, float, float]] | None = None  # (start_sec, end_sec, score)
    analyst_override: str | None = None
    case_note: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)
