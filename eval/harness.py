"""Score a dataset's trials, compute EER, plot a DET curve."""
import os

import numpy as np
from sklearn.metrics import roc_curve

from audio.preprocess import load_audio, preprocess
from audio.telephony import simulate_telephony
from eval.protocols import Trial
from spoof.scorer import score


def score_trials(trials: list[Trial], condition: str = "clean", seed: int = 0,
                  out_path: str | None = None, progress_every: int = 200) -> dict[str, float]:
    """Runs preprocess (+ optional telephony degradation) and the spoof scorer over every trial.
    Returns audio_path -> score, or NaN where VAD rejected the file (or scoring errored).

    If out_path is given, each result is appended and flushed immediately (not batched at the
    end) so a run that dies partway through a many-hour scoring pass loses at most the one
    in-flight trial. A prior partial file at out_path is picked up and those trials are skipped,
    same resume approach as the dataset downloads."""
    already_scored = read_scores(out_path) if out_path and os.path.exists(out_path) else {}
    scores = dict(already_scored)
    remaining = [t for t in trials if t.audio_path not in already_scored]
    if already_scored:
        print(f"resuming: {len(already_scored)} trials already scored, {len(remaining)} left", flush=True)

    out_file = open(out_path, "a") if out_path else None
    try:
        for i, trial in enumerate(remaining, 1):
            try:
                waveform, sr = load_audio(trial.audio_path)
                if condition == "telephony":
                    waveform = simulate_telephony(waveform, sr, out_sr=16000, seed=seed)
                    sr = 16000
                clean = preprocess(waveform, sr)
                s = score(clean, 16000) if clean is not None else float("nan")
            except Exception as e:
                print(f"  error scoring {trial.audio_path}: {e}", flush=True)
                s = float("nan")

            scores[trial.audio_path] = s
            if out_file:
                out_file.write(f"{trial.audio_path} {s}\n")
                out_file.flush()
            if progress_every and i % progress_every == 0:
                print(f"  {i}/{len(remaining)} scored", flush=True)
    finally:
        if out_file:
            out_file.close()
    return scores


def write_scores(scores: dict[str, float], out_path: str) -> None:
    with open(out_path, "w") as f:
        for path, s in scores.items():
            f.write(f"{path} {s}\n")


def read_scores(scores_path: str) -> dict[str, float]:
    scores = {}
    with open(scores_path) as f:
        for line in f:
            path, s = line.rsplit(" ", 1)
            scores[path] = float(s)
    return scores


def _labeled_scores(scores: dict[str, float], trials: list[Trial]) -> tuple[np.ndarray, np.ndarray]:
    """Excludes VAD-rejected (NaN) trials. y=1 means spoof."""
    y_true, y_score = [], []
    for trial in trials:
        s = scores.get(trial.audio_path)
        if s is None or np.isnan(s):
            continue
        y_true.append(1 if trial.label == "spoof" else 0)
        y_score.append(s)
    return np.array(y_true), np.array(y_score)


def compute_eer(scores: dict[str, float], trials: list[Trial]) -> tuple[float, float]:
    """Returns (eer, threshold)."""
    y_true, y_score = _labeled_scores(scores, trials)
    fpr, tpr, thresholds = roc_curve(y_true, y_score)
    fnr = 1 - tpr
    idx = np.nanargmin(np.abs(fnr - fpr))
    return float((fpr[idx] + fnr[idx]) / 2), float(thresholds[idx])


def plot_det_curve(scores: dict[str, float], trials: list[Trial], out_path: str, label: str = "") -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.stats import norm

    y_true, y_score = _labeled_scores(scores, trials)
    fpr, tpr, _ = roc_curve(y_true, y_score)
    fnr = 1 - tpr

    eps = 1e-4
    x = norm.ppf(np.clip(fpr, eps, 1 - eps))
    y = norm.ppf(np.clip(fnr, eps, 1 - eps))

    plt.figure(figsize=(5, 5))
    plt.plot(x, y, label=label or "CM")
    ticks = [0.001, 0.01, 0.05, 0.2, 0.5]
    tick_pos = norm.ppf(ticks)
    plt.xticks(tick_pos, [str(t) for t in ticks])
    plt.yticks(tick_pos, [str(t) for t in ticks])
    plt.xlim(norm.ppf(eps), norm.ppf(0.6))
    plt.ylim(norm.ppf(eps), norm.ppf(0.6))
    plt.xlabel("False Alarm Rate")
    plt.ylabel("Miss Rate")
    plt.title("DET curve")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


if __name__ == "__main__":
    import argparse

    from eval.protocols import parse_asvspoof_protocol, parse_in_the_wild_protocol, subsample_trials

    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["asvspoof", "itw"], required=True)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--audio-dir", required=True)
    parser.add_argument("--audio-ext", default=".flac")
    parser.add_argument("--required-subset", default=None, help='e.g. "eval" to filter ASVspoof2021 metadata rows')
    parser.add_argument("--out-scores", required=True)
    parser.add_argument("--out-det", default=None)
    parser.add_argument("--condition", choices=["clean", "telephony"], default="clean")
    parser.add_argument("--n-samples", type=int, default=None)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    if args.format == "asvspoof":
        trials = parse_asvspoof_protocol(args.protocol, args.audio_dir, ext=args.audio_ext,
                                          required_subset=args.required_subset)
    else:
        trials = parse_in_the_wild_protocol(args.protocol, args.audio_dir)

    if args.n_samples:
        trials = subsample_trials(trials, args.n_samples, seed=args.seed)

    print(f"scoring {len(trials)} trials, condition={args.condition}", flush=True)
    trial_scores = score_trials(trials, condition=args.condition, seed=args.seed, out_path=args.out_scores)

    eer, threshold = compute_eer(trial_scores, trials)
    print(f"EER: {eer * 100:.2f}%  (threshold={threshold:.4f})")

    if args.out_det:
        plot_det_curve(trial_scores, trials, args.out_det, label=f"{args.condition}, EER={eer*100:.2f}%")
