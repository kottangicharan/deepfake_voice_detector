import numpy as np

from audio.telephony import add_background_noise, apply_packet_loss, apply_ulaw, simulate_telephony


def test_ulaw_roundtrip_preserves_length_and_range(real_speech):
    waveform, sr = real_speech
    clip = waveform[: sr * 2]
    out = apply_ulaw(clip)
    assert out.shape == clip.shape
    assert np.abs(out).max() <= 1.0 + 1e-3


def test_packet_loss_zeros_some_samples():
    rng = np.random.default_rng(0)
    signal = rng.normal(0, 1, size=16000).astype(np.float32)
    out = apply_packet_loss(signal, sr=16000, loss_rate=1.0, seed=0)
    assert np.allclose(out, 0.0)


def test_packet_loss_no_loss_is_identity():
    rng = np.random.default_rng(0)
    signal = rng.normal(0, 1, size=16000).astype(np.float32)
    out = apply_packet_loss(signal, sr=16000, loss_rate=0.0, seed=0)
    assert np.array_equal(out, signal)


def test_background_noise_changes_signal():
    rng = np.random.default_rng(0)
    signal = rng.normal(0, 1, size=16000).astype(np.float32)
    out = add_background_noise(signal, snr_db=10.0, seed=1)
    assert not np.array_equal(out, signal)
    assert out.shape == signal.shape


def test_simulate_telephony_returns_requested_sample_rate(real_speech):
    waveform, sr = real_speech
    clip = waveform[: sr * 2]
    out = simulate_telephony(clip, sr, out_sr=16000, seed=0)
    # AMR-NB's frame-based encoding can shift the sample count by a partial frame.
    assert abs(out.shape[0] - 16000 * 2) < 16000 * 0.1
    assert np.isfinite(out).all()
