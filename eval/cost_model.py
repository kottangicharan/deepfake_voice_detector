"""expected_cost(threshold) = P(false_accept) * fraud_loss + P(false_reject) * support_cost

A trial is "flagged" (treated as spoof) when its score >= threshold. False accept = a spoof
trial scored under threshold (fraud gets through); false reject = a bonafide trial scored over
threshold (a real caller gets bounced to support/step-up).
"""
import numpy as np

from eval.protocols import Trial


def _rates_at_threshold(scores: dict[str, float], trials: list[Trial], threshold: float) -> tuple[float, float]:
    fa = fr = n_bonafide = n_spoof = 0
    for trial in trials:
        s = scores.get(trial.audio_path)
        if s is None or np.isnan(s):
            continue
        flagged = s >= threshold
        if trial.label == "bonafide":
            n_bonafide += 1
            fr += flagged
        else:
            n_spoof += 1
            fa += not flagged
    p_fa = fa / n_spoof if n_spoof else 0.0
    p_fr = fr / n_bonafide if n_bonafide else 0.0
    return p_fa, p_fr


def expected_cost(scores: dict[str, float], trials: list[Trial], threshold: float,
                   fraud_loss: float, support_cost: float) -> tuple[float, float, float]:
    p_fa, p_fr = _rates_at_threshold(scores, trials, threshold)
    return p_fa * fraud_loss + p_fr * support_cost, p_fa, p_fr


def cost_curve(scores: dict[str, float], trials: list[Trial], fraud_loss: float,
                support_cost: float, n_thresholds: int = 200) -> list[tuple[float, float, float, float]]:
    """Returns a list of (threshold, cost, p_false_accept, p_false_reject)."""
    values = [s for s in scores.values() if not np.isnan(s)]
    lo, hi = min(values), max(values)
    thresholds = np.linspace(lo, hi, n_thresholds)
    return [(float(t), *expected_cost(scores, trials, t, fraud_loss, support_cost)) for t in thresholds]


def best_operating_point(scores: dict[str, float], trials: list[Trial], fraud_loss: float,
                          support_cost: float, n_thresholds: int = 200) -> tuple[float, float, float, float]:
    curve = cost_curve(scores, trials, fraud_loss, support_cost, n_thresholds)
    return min(curve, key=lambda row: row[1])


def precision_recall_at(scores: dict[str, float], trials: list[Trial], threshold: float) -> tuple[float, float]:
    """Precision/recall for detecting spoof (positive class = spoof, flagged at >= threshold)."""
    tp = fp = fn = 0
    for trial in trials:
        s = scores.get(trial.audio_path)
        if s is None or np.isnan(s):
            continue
        flagged = s >= threshold
        if trial.label == "spoof":
            tp += flagged
            fn += not flagged
        else:
            fp += flagged
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return precision, recall


def plot_cost_curve(curve: list[tuple[float, float, float, float]], best: tuple[float, float, float, float],
                     out_path: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    thresholds = [row[0] for row in curve]
    costs = [row[1] for row in curve]
    plt.figure(figsize=(7, 4.5))
    plt.plot(thresholds, costs, label="expected cost")
    plt.axvline(best[0], color="red", linestyle="--", label=f"chosen threshold = {best[0]:.3f}")
    plt.xlabel("threshold")
    plt.ylabel("expected cost (per call)")
    plt.title("Cost vs threshold")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
