"""Per-dataset protocol parsers -> a common list of Trial(audio_path, label)."""
import csv
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Trial:
    audio_path: str
    label: str  # "bonafide" or "spoof"

    def __post_init__(self):
        if self.label not in ("bonafide", "spoof"):
            raise ValueError(f"invalid label: {self.label!r}")


def _find_label(fields: list[str]) -> str:
    for field in fields:
        if field in ("bonafide", "spoof"):
            return field
    raise ValueError(f"no bonafide/spoof label found in fields: {fields}")


def parse_asvspoof_protocol(protocol_path: str, audio_dir: str, ext: str = ".flac",
                             required_subset: str | None = None) -> list[Trial]:
    """ASVspoof 2019/2021 LA/DF protocol format: whitespace-separated columns, with the
    audio filename always in column 1 and a bonafide/spoof label token somewhere in the row
    (column count and position of everything else differs between the 2019 and 2021 releases).

    The 2021 DF/LA metadata files mix three partitions per a `subset` column ("eval",
    "progress", "hidden") from the live challenge; only "eval" is the standard reported set.
    Pass required_subset="eval" to filter to just that (2019 protocol files have no such
    column and don't need this)."""
    trials = []
    with open(protocol_path) as f:
        for line in f:
            fields = line.split()
            if not fields:
                continue
            if required_subset is not None and required_subset not in fields:
                continue
            filename = fields[1]
            label = _find_label(fields)
            trials.append(Trial(os.path.join(audio_dir, filename + ext), label))
    return trials


def parse_in_the_wild_protocol(meta_csv_path: str, audio_dir: str) -> list[Trial]:
    """In-the-Wild's meta.csv: columns file,speaker,label (label: bona-fide/spoof)."""
    trials = []
    with open(meta_csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = "bonafide" if row["label"].strip().lower() in ("bona-fide", "bonafide") else "spoof"
            trials.append(Trial(os.path.join(audio_dir, row["file"]), label))
    return trials


def subsample_trials(trials: list[Trial], n: int, seed: int = 0) -> list[Trial]:
    """Stratified random subsample, preserving the bonafide/spoof ratio as closely as possible."""
    import random

    rng = random.Random(seed)
    bonafide = [t for t in trials if t.label == "bonafide"]
    spoof = [t for t in trials if t.label == "spoof"]
    frac = n / len(trials)
    n_bonafide = min(len(bonafide), round(len(bonafide) * frac))
    n_spoof = min(len(spoof), round(len(spoof) * frac))
    return rng.sample(bonafide, n_bonafide) + rng.sample(spoof, n_spoof)
