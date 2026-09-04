from risk.policy import DEFAULT_THRESHOLDS, apply_policy
from risk.types import Decision, SignalResult


def _decision(fused_score, fused_confidence=0.9, degraded=False, intent_score=None):
    signals = {}
    if intent_score is not None:
        signals["intent"] = SignalResult(score=intent_score, reason="intent", confidence=0.9)
    return Decision(
        call_id="c1", timestamp="t", claimed_channel="pstn", signals=signals,
        fused_score=fused_score, fused_confidence=fused_confidence,
        action="", abstain=False, reason="", degraded=degraded, degradation_reasons=[],
        threshold_version="", model_versions={},
    )


def test_low_score_allows():
    d = apply_policy(_decision(0.1))
    assert d.action == "allow"
    assert d.abstain is False


def test_mid_score_steps_up():
    d = apply_policy(_decision((DEFAULT_THRESHOLDS.step_up + DEFAULT_THRESHOLDS.block) / 2))
    assert d.action == "step_up"


def test_high_score_blocks():
    d = apply_policy(_decision(0.95))
    assert d.action == "block_and_review"
    assert d.abstain is False


def test_abstain_band_with_low_confidence_abstains():
    mid_abstain = (DEFAULT_THRESHOLDS.abstain_low + DEFAULT_THRESHOLDS.abstain_high) / 2
    d = apply_policy(_decision(mid_abstain, fused_confidence=0.1))
    assert d.abstain is True
    assert d.action == "block_and_review"


def test_abstain_band_with_high_confidence_does_not_abstain():
    mid_abstain = (DEFAULT_THRESHOLDS.abstain_low + DEFAULT_THRESHOLDS.abstain_high) / 2
    d = apply_policy(_decision(mid_abstain, fused_confidence=0.95))
    assert d.abstain is False


def test_intent_escalates_allow_to_block():
    d = apply_policy(_decision(0.1, intent_score=0.9))
    assert d.action == "block_and_review"
    assert "intent" in d.reason


def test_intent_never_downgrades():
    d = apply_policy(_decision(0.95, intent_score=0.0))
    assert d.action == "block_and_review"


def test_degraded_tightens_toward_friction():
    normal = apply_policy(_decision(0.4, degraded=False))
    degraded = apply_policy(_decision(0.4, degraded=True))
    # same raw score, but degraded thresholds are lower -> at least as strict an outcome
    order = {"allow": 0, "step_up": 1, "block_and_review": 2}
    assert order[degraded.action] >= order[normal.action]
