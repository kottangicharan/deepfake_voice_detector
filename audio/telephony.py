"""Telephony channel simulation: 8kHz + AMR-NB + G.711 mu-law + packet loss + noise.

Used both as training/eval augmentation and as its own eval condition (Phase 2).
"""
import audioop  # ponytail: stdlib G.711 codec, deprecated/removed in 3.13+; revisit if we move off 3.11
import os
import subprocess
import tempfile

import numpy as np
import soundfile as sf
import torch
import torchaudio

TELEPHONY_SR = 8000


def _resample(waveform: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return waveform
    wav = torchaudio.functional.resample(torch.as_tensor(waveform, dtype=torch.float32), sr_in, sr_out)
    return wav.numpy()


def apply_ulaw(waveform: np.ndarray) -> np.ndarray:
    """G.711 mu-law encode/decode round trip (quantization artifact)."""
    pcm16 = (np.clip(waveform, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
    ulaw = audioop.lin2ulaw(pcm16, 2)
    pcm16_back = audioop.ulaw2lin(ulaw, 2)
    return np.frombuffer(pcm16_back, dtype=np.int16).astype(np.float32) / 32768.0


def apply_amr_nb(waveform: np.ndarray, sr: int = TELEPHONY_SR) -> np.ndarray:
    """AMR-NB encode/decode round trip via ffmpeg's libopencore_amrnb."""
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = os.path.join(tmp, "in.wav")
        amr_path = os.path.join(tmp, "out.amr")
        out_path = os.path.join(tmp, "out.wav")
        sf.write(wav_path, waveform, sr)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", wav_path, "-ar", str(TELEPHONY_SR), "-ab", "12.2k", amr_path],
            check=True,
        )
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", amr_path, out_path], check=True)
        out, _ = sf.read(out_path, dtype="float32")
    return out


def apply_packet_loss(waveform: np.ndarray, sr: int, loss_rate: float = 0.05, chunk_ms: int = 20, seed=None) -> np.ndarray:
    """Zero out random ~chunk_ms segments at the given loss rate."""
    rng = np.random.default_rng(seed)
    out = waveform.copy()
    chunk = max(1, int(sr * chunk_ms / 1000))
    for start in range(0, len(out), chunk):
        if rng.random() < loss_rate:
            out[start:start + chunk] = 0.0
    return out


def add_background_noise(waveform: np.ndarray, snr_db: float = 15.0, seed=None) -> np.ndarray:
    """Additive white noise at the given SNR."""
    rng = np.random.default_rng(seed)
    signal_power = float(np.mean(waveform ** 2))
    noise = rng.normal(0, 1, size=waveform.shape).astype(np.float32)
    noise_power = float(np.mean(noise ** 2))
    if signal_power == 0 or noise_power == 0:
        return waveform
    noise *= np.sqrt((signal_power / (10 ** (snr_db / 10))) / noise_power)
    return waveform + noise


def simulate_telephony(waveform: np.ndarray, sr: int, out_sr: int = 16000, seed=None) -> np.ndarray:
    """Full degradation pipeline; returns a waveform resampled back to out_sr for scoring."""
    wav = _resample(np.asarray(waveform, dtype=np.float32), sr, TELEPHONY_SR)
    wav = apply_amr_nb(wav, TELEPHONY_SR)
    wav = apply_ulaw(wav)
    wav = add_background_noise(wav, seed=seed)
    wav = apply_packet_loss(wav, TELEPHONY_SR, seed=seed)
    return _resample(wav, TELEPHONY_SR, out_sr)
