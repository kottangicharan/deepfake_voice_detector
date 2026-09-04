"""Combines the four signals into one fused risk score with an abstain-aware confidence.

Not Platt/isotonic calibrated — no fusion-level labeled dataset exists yet (that would need
labeled examples scored across all four signals together, not just the spoof-only eval grid in
eval/). Starts with a documented weighted sum instead, per the spec's own "start with weighted
sum" guidance, honest about the gap rather than overclaiming.
"""
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from audio.preprocess import preprocess
from risk.degradation import insufficient_audio_decision, run_signal_safely
from risk.policy import DEFAULT_THRESHOLDS, apply_policy
from risk.types import Decision, SignalResult
from signals.channel import analyze_channel
from signals.voiceprint import verify as voiceprint_verify
from spoof.scorer import score as spoof_score
from spoof.scorer import score_windows

DEFAULT_WEIGHTS = {"spoof": 0.5, "channel": 0.2, "voiceprint": 0.3}  # intent is a policy-level escalation, never blended
FUSION_VERSION = "fusion-v1-weighted-sum-uncalibrated"
MODEL_VERSIONS = {
    "spoof": "rawtfnet-32",
    "channel": "rule-based-fft-v1",
    "voiceprint": "speechbrain-ecapa-voxceleb",
    "intent": "unavailable",
}

_CALIBRATION_PATH = Path(__file__).resolve().parent / "spoof_calibration.json"
_DEFAULT_CALIBRATION = {"p_low": 0.0, "p_high": 1.0}  # no-op stretch if calibration hasn't been fit


def _load_calibration() -> dict:
    if _CALIBRATION_PATH.exists():
        return json.loads(_CALIBRATION_PATH.read_text())
    return _DEFAULT_CALIBRATION


def rescale_spoof_score(raw: float, calib: dict) -> float:
    """Stretches raw from the observed [p_low, p_high] saturated range to [0, 1], clipping outside it."""
    lo, hi = calib["p_low"], calib["p_high"]
    if hi <= lo:
        return raw
    return float(np.clip((raw - lo) / (hi - lo), 0.0, 1.0))


def run_signals(waveform: np.ndarray, sr: int, claimed_channel: str = "unknown",
                 enrolled_embedding: np.ndarray | None = None,
                 intent_result: SignalResult | None = None) -> tuple[dict[str, SignalResult], bool, list[str]]:
    """Runs each signal through degradation.run_signal_safely; voiceprint is skipped (score=None)
    with no enrollment. Returns (signals, degraded, degradation_reasons)."""
    signals: dict[str, SignalResult] = {}
    degradation_reasons: list[str] = []

    spoof_result, reason = run_signal_safely("spoof", lambda: spoof_score(waveform, sr))
    signals["spoof"] = spoof_result
    if reason:
        degradation_reasons.append(reason)

    channel_result, reason = run_signal_safely("channel", lambda: analyze_channel(waveform, sr, claimed_channel))
    signals["channel"] = channel_result
    if reason:
        degradation_reasons.append(reason)

    if enrolled_embedding is None:
        signals["voiceprint"] = SignalResult(score=None, reason="no enrollment for this call", confidence=0.0)
    else:
        voiceprint_result, reason = run_signal_safely("voiceprint", lambda: voiceprint_verify(waveform, sr, enrolled_embedding))
        signals["voiceprint"] = voiceprint_result
        if reason:
            degradation_reasons.append(reason)

    signals["intent"] = intent_result if intent_result is not None else SignalResult(
        score=None, reason="intent signal not configured", confidence=0.0
    )

    return signals, len(degradation_reasons) > 0, degradation_reasons


def fuse(signals: dict[str, SignalResult], weights: dict[str, float] = DEFAULT_WEIGHTS,
         calib: dict | None = None) -> tuple[float, float]:
    """Weighted sum over whichever of spoof/channel/voiceprint have a score, renormalized by the
    weight of the available subset. Spoof is rescaled first. Returns (fused_score, fused_confidence)."""
    calib = calib if calib is not None else _load_calibration()

    weighted_sum = 0.0
    confidence_sum = 0.0
    weight_total = 0.0
    for name, weight in weights.items():
        result = signals.get(name)
        if result is None or result.score is None:
            continue
        value = rescale_spoof_score(result.score, calib) if name == "spoof" else result.score
        weighted_sum += weight * value
        confidence_sum += weight * result.confidence
        weight_total += weight

    if weight_total == 0.0:
        return 0.5, 0.0  # nothing usable — maximally uncertain, not a false "safe" 0

    return weighted_sum / weight_total, confidence_sum / weight_total


def decide(waveform: np.ndarray, sr: int, call_id: str, claimed_channel: str = "unknown",
           enrolled_embedding: np.ndarray | None = None, intent_result: SignalResult | None = None,
           thresholds=DEFAULT_THRESHOLDS, compute_timeline: bool = True) -> Decision:
    """The single orchestration entry point: preprocess -> signals -> fuse -> policy."""
    clean = preprocess(waveform, sr)
    if clean is None:
        return insufficient_audio_decision(call_id, claimed_channel, "n/a", MODEL_VERSIONS)

    signals, degraded, degradation_reasons = run_signals(
        clean, 16000, claimed_channel=claimed_channel,
        enrolled_embedding=enrolled_embedding, intent_result=intent_result,
    )
    fused_score, fused_confidence = fuse(signals)

    decision = Decision(
        call_id=call_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        claimed_channel=claimed_channel,
        signals=signals,
        fused_score=fused_score,
        fused_confidence=fused_confidence,
        action="",
        abstain=False,
        reason="",
        degraded=degraded,
        degradation_reasons=degradation_reasons,
        threshold_version="",
        model_versions=MODEL_VERSIONS,
    )
    decision = apply_policy(decision, thresholds)

    if compute_timeline:
        decision.spoof_timeline = score_windows(clean)

    return decision
