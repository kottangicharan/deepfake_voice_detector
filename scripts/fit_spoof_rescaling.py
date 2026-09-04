"""One-off: fit spoof-score rescaling bounds from real eval scores, write risk/spoof_calibration.json.

The raw spoof score saturates near 1.0 for almost everything (see docs/METRICS.md) — p1/p99 of the
observed distribution is a far more useful [low, high] stretch range than the theoretical [0, 1].
Rerun this once results/scores_itw_clean.txt (or a fuller eval run) has more data; it's a derived
artifact, not source, hence gitignored.
"""
import json
import sys
from pathlib import Path

import numpy as np

SCORES_PATH = Path(__file__).resolve().parent.parent / "results" / "scores_itw_clean.txt"
OUT_PATH = Path(__file__).resolve().parent.parent / "risk" / "spoof_calibration.json"


def fit(scores_path: Path = SCORES_PATH) -> dict:
    values = []
    with open(scores_path) as f:
        for line in f:
            _, s = line.rsplit(" ", 1)
            s = float(s)
            if not np.isnan(s):
                values.append(s)
    values = np.array(values)
    p_low, p_high = float(np.percentile(values, 1)), float(np.percentile(values, 99))
    return {
        "p_low": p_low,
        "p_high": p_high,
        "n_samples": len(values),
        "source": str(scores_path.name),
    }


if __name__ == "__main__":
    calib = fit()
    OUT_PATH.write_text(json.dumps(calib, indent=2))
    print(f"wrote {OUT_PATH}: {calib}")
