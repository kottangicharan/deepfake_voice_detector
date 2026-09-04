from audio.preprocess import preprocess
from spoof.scorer import score, score_windows


def test_score_returns_float_in_unit_range(real_speech):
    waveform, sr = real_speech
    clean = preprocess(waveform, sr)
    assert clean is not None

    result = score(clean, 16000)
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0


def test_score_windows_covers_the_clip(real_speech):
    waveform, sr = real_speech
    clean = preprocess(waveform, sr)
    assert clean is not None

    windows = score_windows(clean, window_sec=1.0, hop_sec=0.5)
    assert len(windows) > 1
    for start, end, s in windows:
        assert 0.0 <= s <= 1.0
        assert end > start
    assert windows[0][0] == 0.0
    assert windows[-1][1] == len(clean) / 16000


def test_score_windows_short_clip_returns_single_window():
    import numpy as np

    short = np.zeros(8000, dtype=np.float32)  # 0.5s, shorter than the 1s window
    windows = score_windows(short, window_sec=1.0, hop_sec=0.5)
    assert len(windows) == 1
    assert windows[0][0] == 0.0
