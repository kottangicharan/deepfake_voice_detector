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
    """Loads audio as mono float32. Falls back to librosa's audioread/ffmpeg backend when
    soundfile's libFLAC can't decode a file that's otherwise structurally valid — a real
    libsndfile compatibility gap hit on a meaningful fraction of ASVspoof2021 DF's FLACs
    (confirmed valid: correct fLaC header, reads fine in ffprobe), not actual corruption."""
    try:
        waveform, sr = sf.read(path, dtype="float32", always_2d=True)
        return waveform.mean(axis=1), sr
    except Exception:
        import librosa

        waveform, sr = librosa.load(path, sr=None, mono=True)
        return waveform.astype(np.float32), sr


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
