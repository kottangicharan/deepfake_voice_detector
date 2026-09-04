import numpy as np
from scipy.signal import butter, filtfilt

from signals.channel import analyze_channel, estimate_bandwidth

SR = 16000


def _lowpassed_noise(cutoff_hz: float, seed: int = 0, duration_sec: float = 2.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, size=int(SR * duration_sec)).astype(np.float64)
    b, a = butter(8, cutoff_hz / (SR / 2), btype="low")
    return filtfilt(b, a, noise).astype(np.float32)


def test_estimate_bandwidth_detects_narrowband_cutoff():
    signal = _lowpassed_noise(3000)
    bandwidth = estimate_bandwidth(signal, SR)
    assert 2000 < bandwidth < 4000


def test_estimate_bandwidth_detects_wideband_cutoff():
    signal = _lowpassed_noise(7000)
    bandwidth = estimate_bandwidth(signal, SR)
    assert 5500 < bandwidth < 7800


def test_analyze_channel_matches_claimed_pstn():
    signal = _lowpassed_noise(3000)
    result = analyze_channel(signal, SR, claimed_channel="pstn")
    assert result["score"] < 0.2


def test_analyze_channel_flags_fullband_audio_claiming_pstn():
    rng = np.random.default_rng(0)
    signal = rng.normal(0, 1, size=SR * 2).astype(np.float32)  # unfiltered, full-band
    result = analyze_channel(signal, SR, claimed_channel="pstn")
    assert result["score"] > 0.3


def test_analyze_channel_unknown_claimed_channel_returns_zero():
    signal = _lowpassed_noise(3000)
    result = analyze_channel(signal, SR, claimed_channel="carrier_pigeon")
    assert result["score"] == 0.0
    assert result["confidence"] == 0.0
