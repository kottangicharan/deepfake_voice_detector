"""Wraps RawTFNet (third_party/rawtfnet) behind score(waveform, sr) -> float.

Nes2Net_ASVspoof_ITW (the spec's primary reference) needs fairseq, which fails to
install on this machine for three independent reasons: a Windows symlink-privilege
error in its setup.py, a missing MSVC C++ compiler for its C extensions, and a
Python 3.11 dataclass incompatibility baked into fairseq's own config classes
(`field: Config = Config()` is rejected as a mutable default). RawTFNet-Pytorch is
the spec's own designated CPU fallback: pure PyTorch, no fairseq, checkpoint
bundled in the repo.
"""
import sys
from pathlib import Path

import numpy as np
import torch

_RAWTFNET_DIR = Path(__file__).resolve().parent.parent / "third_party" / "rawtfnet"
_CKPT_PATH = _RAWTFNET_DIR / "ckpts" / "Best_RawTFNet_32.pth"
_SCORE_LEN = 64600  # ~4.04s @ 16kHz, the convention used throughout RawTFNet's own eval code

if str(_RAWTFNET_DIR) not in sys.path:
    sys.path.insert(0, str(_RAWTFNET_DIR))

_model = None


def _pad_or_tile(x: np.ndarray, max_len: int = _SCORE_LEN) -> np.ndarray:
    x_len = x.shape[0]
    if x_len >= max_len:
        return x[:max_len]
    num_repeats = int(max_len / x_len) + 1
    return np.tile(x, num_repeats)[:max_len]


def _get_model():
    global _model
    if _model is None:
        from model_scripts.rawtfnet import RawTFNet

        model = RawTFNet(sample_rate=16000)
        state_dict = torch.load(_CKPT_PATH, map_location="cpu")
        model.load_state_dict(state_dict)
        model.eval()
        _model = model
    return _model


def score(waveform: np.ndarray, sr: int) -> float:
    """Returns spoof risk in [0, 1] for a mono 16kHz waveform (higher = more likely synthetic)."""
    if sr != 16000:
        raise ValueError(f"expected 16kHz audio, got {sr}Hz — run audio.preprocess first")

    x = _pad_or_tile(np.asarray(waveform, dtype=np.float32))
    x = torch.from_numpy(x).unsqueeze(0)

    with torch.no_grad():
        logits = _get_model()(x).reshape(-1, 2)  # TfSepNet squeezes the batch dim away at batch_size=1
        probs = torch.softmax(logits, dim=-1)

    return probs[0, 0].item()  # index 1 is bonafide by RawTFNet's own convention; index 0 is spoof


def score_windows(waveform: np.ndarray, window_sec: float = 1.0, hop_sec: float = 0.5) -> list[tuple[float, float, float]]:
    """Slides score() over a 16kHz waveform. Returns [(start_sec, end_sec, score), ...] —
    what backs a "suspicious region" view; score() alone is whole-clip only."""
    sr = 16000
    window = int(window_sec * sr)
    hop = int(hop_sec * sr)
    n = len(waveform)

    if n <= window:
        return [(0.0, n / sr, score(waveform, sr))]

    windows = []
    start = 0
    while start < n:
        end = min(start + window, n)
        windows.append((start / sr, end / sr, score(waveform[start:end], sr)))
        if end == n:
            break
        start += hop
    return windows


if __name__ == "__main__":
    import argparse

    from audio.preprocess import load_audio, preprocess

    parser = argparse.ArgumentParser()
    parser.add_argument("audio_file")
    args = parser.parse_args()

    raw_waveform, raw_sr = load_audio(args.audio_file)
    clean = preprocess(raw_waveform, raw_sr)
    if clean is None:
        print("ABSTAIN: under 1.5s of usable speech survived VAD")
    else:
        print(score(clean, 16000))
