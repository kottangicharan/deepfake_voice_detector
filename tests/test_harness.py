import math

import soundfile as sf

from eval.harness import compute_eer, read_scores, score_trials, write_scores
from eval.protocols import Trial


def test_compute_eer_perfect_separation():
    trials = [Trial("s1", "spoof"), Trial("s2", "spoof"), Trial("b1", "bonafide"), Trial("b2", "bonafide")]
    scores = {"s1": 0.9, "s2": 0.8, "b1": 0.2, "b2": 0.1}
    eer, _ = compute_eer(scores, trials)
    assert eer == 0.0


def test_compute_eer_excludes_nan():
    trials = [Trial("s1", "spoof"), Trial("s2", "spoof"), Trial("b1", "bonafide")]
    scores = {"s1": float("nan"), "s2": 0.9, "b1": 0.1}
    eer, _ = compute_eer(scores, trials)
    assert eer == 0.0


def test_write_read_scores_roundtrip(tmp_path):
    scores = {"a.flac": 0.123456, "b.flac": 0.987654}
    path = tmp_path / "scores.txt"
    write_scores(scores, str(path))
    assert read_scores(str(path)) == scores


def test_score_trials_end_to_end(tmp_path, real_speech):
    waveform, sr = real_speech
    audio_path = tmp_path / "clip.flac"
    sf.write(str(audio_path), waveform, sr)

    trials = [Trial(str(audio_path), "bonafide")]
    scores = score_trials(trials, condition="clean")
    result = scores[str(audio_path)]
    assert not math.isnan(result)
    assert 0.0 <= result <= 1.0


def test_score_trials_writes_incrementally_and_resumes(tmp_path, real_speech):
    waveform, sr = real_speech
    audio_path = tmp_path / "clip.flac"
    sf.write(str(audio_path), waveform, sr)
    out_path = tmp_path / "scores.txt"

    trials = [Trial(str(audio_path), "bonafide")]
    score_trials(trials, condition="clean", out_path=str(out_path))
    assert out_path.exists()
    on_disk = read_scores(str(out_path))
    assert str(audio_path) in on_disk

    # a second call with the same out_path should skip already-scored trials, not duplicate them
    score_trials(trials, condition="clean", out_path=str(out_path))
    lines = out_path.read_text().strip().splitlines()
    assert len(lines) == 1


def test_score_trials_skips_unreadable_file_instead_of_crashing(tmp_path):
    trials = [Trial(str(tmp_path / "does_not_exist.flac"), "spoof")]
    scores = score_trials(trials, condition="clean")
    assert math.isnan(scores[str(tmp_path / "does_not_exist.flac")])
