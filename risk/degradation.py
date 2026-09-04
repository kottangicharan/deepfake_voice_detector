"""Degrade closed, never fail open: a signal that errors gets excluded, not trusted; a decision
that can't run at all becomes a block-and-review, never a silent allow.
"""
from dataclasses import replace
from datetime import datetime, timezone
from typing import Callable

from risk.types import Decision, SignalResult

SIGNAL_UNAVAILABLE_MARGIN = 0.10  # ponytail: fixed margin, not learned — revisit once real degraded-mode incidents exist


def run_signal_safely(name: str, fn: Callable[[], dict | float]) -> tuple[SignalResult, str | None]:
    """Runs a zero-arg signal call, catching anything (OOM, missing weights, bad input) so one
    signal failing never crashes the whole decision. Returns (result, degradation_reason_or_None)."""
    try:
        result = fn()
    except Exception as e:
        reason = f"{name} signal unavailable: {e}"
        return SignalResult(score=None, reason=reason, confidence=0.0), reason

    if isinstance(result, dict):
        return SignalResult(score=result["score"], reason=result["reason"], confidence=result.get("confidence", 0.0)), None
    return SignalResult(score=float(result), reason=f"{name} score", confidence=1.0), None


def insufficient_audio_decision(call_id: str, claimed_channel: str, threshold_version: str,
                                 model_versions: dict[str, str]) -> Decision:
    """Built when audio.preprocess.preprocess() returns None (under 1.5s of usable speech)."""
    return Decision(
        call_id=call_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        claimed_channel=claimed_channel,
        signals={},
        fused_score=None,
        fused_confidence=0.0,
        action="block_and_review",
        abstain=True,
        reason="ABSTAIN: insufficient_audio",
        degraded=False,
        degradation_reasons=[],
        threshold_version=threshold_version,
        model_versions=model_versions,
    )


def tighten_thresholds(thresholds: "PolicyThresholds", degraded: bool) -> "PolicyThresholds":
    """When any signal degraded, shrink the step_up/block/abstain bounds so the policy leans
    toward friction rather than trusting a partially-blind decision."""
    if not degraded:
        return thresholds

    m = SIGNAL_UNAVAILABLE_MARGIN
    return replace(
        thresholds,
        step_up=max(0.0, thresholds.step_up - m),
        block=max(0.0, thresholds.block - m),
        abstain_low=max(0.0, thresholds.abstain_low - m),
        abstain_high=max(0.0, thresholds.abstain_high - m),
    )
