"""Maps a fused risk score to a decision: allow | step_up | block_and_review, plus abstain.

This is NOT eval.cost_model — that module sweeps thresholds over a labeled dataset offline to
find where P(false_accept)*fraud_loss + P(false_reject)*support_cost is minimized. This module
applies a threshold *once decided*, per live call, with no trial list to sweep. The thresholds
below are heuristic, chosen with the same cost-tradeoff reasoning (a false accept on a settlement
change is far costlier than one extra step-up), not fit against a labeled fusion-level dataset —
no such dataset exists yet. Say so rather than imply a calibration that hasn't happened.
"""
from dataclasses import dataclass, replace

from risk.degradation import tighten_thresholds
from risk.types import Decision

THRESHOLD_VERSION = "policy-v1-heuristic-2026-09-04"
INTENT_ESCALATE_THRESHOLD = 0.7


@dataclass(frozen=True)
class PolicyThresholds:
    step_up: float = 0.35
    block: float = 0.75
    abstain_low: float = 0.45
    abstain_high: float = 0.65
    min_confidence_for_autonomy: float = 0.3


DEFAULT_THRESHOLDS = PolicyThresholds()


def apply_policy(decision: Decision, thresholds: PolicyThresholds = DEFAULT_THRESHOLDS) -> Decision:
    """Reads decision.fused_score/.fused_confidence/.degraded/.signals, sets
    decision.action/.abstain/.reason in place, and returns it."""
    thresholds = tighten_thresholds(thresholds, decision.degraded)
    score = decision.fused_score

    if thresholds.abstain_low <= score < thresholds.abstain_high and decision.fused_confidence < thresholds.min_confidence_for_autonomy:
        decision.abstain = True
        decision.action = "block_and_review"
        decision.reason = f"ABSTAIN: fused score {score:.3f} in the abstain band with low confidence ({decision.fused_confidence:.3f})"
    elif score >= thresholds.block:
        decision.action = "block_and_review"
        decision.reason = f"fused score {score:.3f} at or above block threshold {thresholds.block:.3f}"
    elif score >= thresholds.step_up:
        decision.action = "step_up"
        decision.reason = f"fused score {score:.3f} at or above step_up threshold {thresholds.step_up:.3f}"
    else:
        decision.action = "allow"
        decision.reason = f"fused score {score:.3f} below step_up threshold {thresholds.step_up:.3f}"

    intent = decision.signals.get("intent")
    if intent is not None and intent.score is not None and intent.score >= INTENT_ESCALATE_THRESHOLD:
        if decision.action != "block_and_review":
            decision.action = "block_and_review"
            decision.reason += f"; escalated by intent signal ({intent.score:.3f} >= {INTENT_ESCALATE_THRESHOLD})"

    decision.threshold_version = THRESHOLD_VERSION
    return decision
