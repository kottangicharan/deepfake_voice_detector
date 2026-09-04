import numpy as np
import soundfile as sf

from audio.preprocess import TARGET_SR, load_audio, preprocess


def test_load_audio_reads_a_normal_wav(tmp_path, real_speech):
    waveform, sr = real_speech
    path = tmp_path / "clip.wav"
    sf.write(str(path), waveform, sr)

    loaded, loaded_sr = load_audio(str(path))
    assert loaded_sr == sr
    assert loaded.shape[0] == waveform.shape[0]


def test_load_audio_falls_back_to_librosa_when_soundfile_fails(tmp_path, real_speech, monkeypatch):
    waveform, sr = real_speech
    path = tmp_path / "clip.wav"
    sf.write(str(path), waveform, sr)

    import audio.preprocess as preprocess_module

    def broken_read(*args, **kwargs):
        raise RuntimeError("simulated libsndfile decode failure")

    monkeypatch.setattr(preprocess_module.sf, "read", broken_read)

    loaded, loaded_sr = load_audio(str(path))
    assert loaded_sr == sr
    assert loaded.shape[0] > 0


def test_normal_clip_passes_through(real_speech):
    waveform, sr = real_speech
    result = preprocess(waveform, sr)
    assert result is not None
    assert result.dtype == np.float32
    assert np.abs(result).max() <= 1.0 + 1e-6


def test_silent_clip_rejected():
    silence = np.zeros(int(3 * TARGET_SR), dtype=np.float32)
    assert preprocess(silence, TARGET_SR) is None


def test_too_short_clip_rejected(real_speech):
    waveform, sr = real_speech
    half_second = waveform[: int(0.5 * sr)]
    assert preprocess(half_second, sr) is None


def test_wrong_sample_rate_gets_resampled(real_speech):
    waveform, sr = real_speech
    import torchaudio
    import torch

    resampled_8k = torchaudio.functional.resample(
        torch.as_tensor(waveform, dtype=torch.float32), sr, 8000
    ).numpy()

    result = preprocess(resampled_8k, 8000)
    assert result is not None
