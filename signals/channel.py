"""Channel-consistency check: does the audio's spectral bandwidth match the claimed call path?

A narrowband PSTN/telephony leg caps content near 3.4kHz (G.711); VoIP/wideband codecs (AMR-WB,
Opus) reach ~7-8kHz; a native app mic capture is effectively full-band. If a caller claims one
path but the spectrum shows another, that's a real signal a cloned-audio injection attack (e.g.
playing synthetic audio into a call rather than through the claimed live mic) can leave behind —
nobody else in this space bothers building it, per the brief.
"""
import numpy as np

CHANNEL_BANDS = {
    "pstn": (300, 3400),
    "voip": (50, 7000),
    "app": (20, 20000),  # effectively unbounded below Nyquist
}


def estimate_bandwidth(waveform: np.ndarray, sr: int, energy_threshold_db: float = -40.0) -> float:
    """Returns the highest frequency (Hz) whose energy is within energy_threshold_db of the peak."""
    spectrum = np.abs(np.fft.rfft(waveform * np.hanning(len(waveform))))
    freqs = np.fft.rfftfreq(len(waveform), d=1 / sr)
    power_db = 20 * np.log10(spectrum + 1e-12)
    peak_db = power_db.max()
    above_floor = np.where(power_db >= peak_db + energy_threshold_db)[0]
    if len(above_floor) == 0:
        return 0.0
    return float(freqs[above_floor[-1]])


def analyze_channel(waveform: np.ndarray, sr: int, claimed_channel: str = "unknown") -> dict:
    """Returns {score, reason, confidence}. score in [0, 1], higher = more suspicious mismatch."""
    bandwidth = estimate_bandwidth(waveform, sr)
    nyquist = sr / 2

    if claimed_channel not in CHANNEL_BANDS:
        return {
            "score": 0.0,
            "reason": f"estimated bandwidth {bandwidth:.0f}Hz; no claimed channel to compare against",
            "confidence": 0.0,
        }

    lo, hi = CHANNEL_BANDS[claimed_channel]
    hi = min(hi, nyquist)

    if bandwidth <= hi * 1.15:
        score = 0.0
        reason = f"bandwidth {bandwidth:.0f}Hz consistent with claimed '{claimed_channel}' path (expected up to ~{hi:.0f}Hz)"
    else:
        # how far bandwidth overshoots the claimed channel's expected ceiling, normalized to [0, 1]
        overshoot = (bandwidth - hi) / max(nyquist - hi, 1.0)
        score = float(np.clip(overshoot, 0.0, 1.0))
        reason = (f"bandwidth {bandwidth:.0f}Hz exceeds claimed '{claimed_channel}' path's expected "
                   f"~{hi:.0f}Hz ceiling — audio may not have actually traveled that path")

    # confidence: a sharp spectral cutoff is a clearer signal than a gradual rolloff
    bw_at_tighter_floor = estimate_bandwidth(waveform, sr, energy_threshold_db=-20.0)
    sharpness = 1.0 - min(abs(bandwidth - bw_at_tighter_floor) / max(bandwidth, 1.0), 1.0)
    confidence = float(np.clip(sharpness, 0.1, 1.0))

    return {"score": score, "reason": reason, "confidence": confidence}
