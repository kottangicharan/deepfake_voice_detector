import librosa
import numpy as np
import pytest


@pytest.fixture(scope="session")
def real_speech():
    """A real bona fide speech clip (LibriSpeech, via librosa's example index)."""
    path = librosa.example("libri1")
    waveform, sr = librosa.load(path, sr=None, mono=True)
    return waveform.astype(np.float32), sr
