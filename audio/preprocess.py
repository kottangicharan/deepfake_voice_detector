"""Load -> resample to 16kHz -> VAD trim -> normalize. Rejects short/silent input."""
import numpy as np
import soundfile as sf
import torch
import torchaudio
from silero_vad import get_speech_timestamps, load_silero_vad

TARGET_SR = 16000
MIN_SPEECH_SAMPLES = int(1.5 * TARGET_SR)

_vad_model = None


def _get_vad_model():
    global _vad_model
    if _vad_model is None:
        _vad_model = load_silero_vad()
    return _vad_model


def load_audio(path: str) -> tuple[np.ndarray, int]:
    waveform, sr = sf.read(path, dtype="float32", always_2d=True)
    return waveform.mean(axis=1), sr


def preprocess(waveform: np.ndarray, sr: int) -> np.ndarray | None:
    """Returns a mono float32 waveform at 16kHz, or None if under 1.5s of speech survives VAD."""
    wav = torch.as_tensor(waveform, dtype=torch.float32)
    if sr != TARGET_SR:
        wav = torchaudio.functional.resample(wav, sr, TARGET_SR)

    timestamps = get_speech_timestamps(wav, _get_vad_model(), sampling_rate=TARGET_SR)
    if not timestamps:
        return None

    speech = torch.cat([wav[ts["start"]:ts["end"]] for ts in timestamps])
    if speech.shape[0] < MIN_SPEECH_SAMPLES:
        return None

    peak = speech.abs().max()
    if peak > 0:
        speech = speech / peak
    return speech.numpy()
