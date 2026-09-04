from dataclasses import dataclass

from risk.degradation import insufficient_audio_decision, run_signal_safely, tighten_thresholds


def test_run_signal_safely_wraps_dict_result():
    result, reason = run_signal_safely("channel", lambda: {"score": 0.4, "reason": "ok", "confidence": 0.8})
    assert result.score == 0.4
    assert result.confidence == 0.8
    assert reason is None


def test_run_signal_safely_wraps_float_result():
    result, reason = run_signal_safely("spoof", lambda: 0.9)
    assert result.score == 0.9
    assert reason is None


def test_run_signal_safely_catches_exceptions():
    def boom():
        raise RuntimeError("model OOM")

    result, reason = run_signal_safely("spoof", boom)
    assert result.score is None
    assert "model OOM" in result.reason
    assert reason is not None


def test_insufficient_audio_decision_blocks_and_abstains():
    decision = insufficient_audio_decision("call1", "pstn", "v1", {"spoof": "rawtfnet"})
    assert decision.action == "block_and_review"
    assert decision.abstain is True
    assert decision.fused_score is None
    assert "insufficient_audio" in decision.reason


@dataclass(frozen=True)
class _FakeThresholds:
    step_up: float = 0.35
    block: float = 0.75
    abstain_low: float = 0.45
    abstain_high: float = 0.65


def test_tighten_thresholds_shrinks_when_degraded():
    base = _FakeThresholds()
    tightened = tighten_thresholds(base, degraded=True)
    assert tightened.step_up < base.step_up
    assert tightened.block < base.block


def test_tighten_thresholds_noop_when_not_degraded():
    base = _FakeThresholds()
    assert tighten_thresholds(base, degraded=False) == base
