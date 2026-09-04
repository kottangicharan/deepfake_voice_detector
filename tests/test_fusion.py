import numpy as np
import pytest
import soundfile as sf

from risk.fusion import decide, fuse, rescale_spoof_score, run_signals
from risk.types import SignalResult


def test_rescale_spoof_score_stretches_saturated_range():
    calib = {"p_low": 0.98, "p_high": 1.0}
    assert rescale_spoof_score(0.98, calib) == 0.0
    assert rescale_spoof_score(1.0, calib) == 1.0
    assert rescale_spoof_score(0.99, calib) == 0.5


def test_rescale_spoof_score_clips_outside_range():
    calib = {"p_low": 0.98, "p_high": 1.0}
    assert rescale_spoof_score(0.5, calib) == 0.0
    assert rescale_spoof_score(1.5, calib) == 1.0


def test_fuse_renormalizes_over_available_signals():
    signals = {
        "spoof": SignalResult(score=None, reason="n/a", confidence=0.0),
        "channel": SignalResult(score=0.8, reason="mismatch", confidence=1.0),
        "voiceprint": SignalResult(score=None, reason="no enrollment", confidence=0.0),
    }
    fused_score, fused_confidence = fuse(signals, weights={"spoof": 0.5, "channel": 0.2, "voiceprint": 0.3})
    assert fused_score == pytest.approx(0.8)  # only channel available -> its value dominates entirely
    assert fused_confidence == pytest.approx(1.0)


def test_fuse_returns_uncertain_when_nothing_available():
    signals = {
        "spoof": SignalResult(score=None, reason="n/a", confidence=0.0),
        "channel": SignalResult(score=None, reason="n/a", confidence=0.0),
        "voiceprint": SignalResult(score=None, reason="n/a", confidence=0.0),
    }
    fused_score, fused_confidence = fuse(signals)
    assert fused_score == 0.5
    assert fused_confidence == 0.0


def test_run_signals_skips_voiceprint_without_enrollment(real_speech):
    waveform, sr = real_speech
    from audio.preprocess import preprocess

    clean = preprocess(waveform, sr)
    signals, degraded, reasons = run_signals(clean, 16000, claimed_channel="pstn")
    assert signals["voiceprint"].score is None
    assert "spoof" in signals and "channel" in signals


def test_decide_end_to_end_returns_full_decision(tmp_path, real_speech):
    waveform, sr = real_speech
    audio_path = tmp_path / "clip.flac"
    sf.write(str(audio_path), waveform, sr)

    import soundfile as sf2
    loaded, loaded_sr = sf2.read(str(audio_path))
    decision = decide(loaded, loaded_sr, call_id="test-call-1", claimed_channel="app")

    assert decision.call_id == "test-call-1"
    assert decision.action in ("allow", "step_up", "block_and_review")
    assert decision.fused_score is not None
    assert 0.0 <= decision.fused_score <= 1.0
    assert decision.spoof_timeline is not None
    assert len(decision.spoof_timeline) >= 1


def test_decide_abstains_on_insufficient_audio():
    silence = np.zeros(int(0.3 * 16000), dtype=np.float32)  # 0.3s, well under the 1.5s VAD floor
    decision = decide(silence, 16000, call_id="test-call-2")
    assert decision.abstain is True
    assert decision.action == "block_and_review"
    assert decision.fused_score is None
