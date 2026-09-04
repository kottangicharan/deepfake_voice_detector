import numpy as np
import pytest
import torch
import torchaudio

from signals.voiceprint import enroll, verify


@pytest.fixture
def speech_16k(real_speech):
    waveform, sr = real_speech
    wav = torchaudio.functional.resample(torch.as_tensor(waveform, dtype=torch.float32), sr, 16000)
    return wav.numpy(), 16000


def test_same_speaker_scores_low_mismatch(speech_16k):
    waveform, sr = speech_16k
    half = len(waveform) // 2
    enrolled = enroll(waveform[:half], sr)
    result = verify(waveform[half:], sr, enrolled)
    assert result["score"] < 0.4


def test_different_signal_scores_higher_mismatch(speech_16k):
    waveform, sr = speech_16k
    enrolled = enroll(waveform[: sr * 2], sr)
    rng = np.random.default_rng(0)
    impostor = rng.normal(0, 0.1, size=sr * 2).astype(np.float32)
    result = verify(impostor, sr, enrolled)
    same_speaker_result = verify(waveform[sr * 2: sr * 4], sr, enrolled)
    assert result["score"] > same_speaker_result["score"]


def test_wrong_sample_rate_rejected(real_speech):
    waveform, sr = real_speech
    try:
        enroll(waveform, 8000)
        assert False, "expected ValueError"
    except ValueError:
        pass
