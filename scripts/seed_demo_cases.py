"""Populates the case queue with a handful of real clips via POST /score, so the analyst
console has something to show before a live demo."""
import sys
from pathlib import Path

import requests

API_BASE = "http://127.0.0.1:8123"
ITW_DIR = Path("C:/eval_data/in_the_wild/release_in_the_wild")
DEMO_FILES = ["1.wav", "2.wav", "5.wav", "7.wav", "9.wav", "10.wav"]
CHANNELS = ["app", "pstn", "voip", "app", "pstn", "app"]

if __name__ == "__main__":
    for filename, channel in zip(DEMO_FILES, CHANNELS):
        path = ITW_DIR / filename
        if not path.exists():
            print(f"skip (missing): {path}")
            continue
        with open(path, "rb") as f:
            resp = requests.post(f"{API_BASE}/score", files={"audio": (filename, f, "audio/wav")},
                                  data={"claimed_channel": channel})
        if resp.status_code != 200:
            print(f"FAILED {filename}: {resp.status_code} {resp.text}", file=sys.stderr)
            continue
        body = resp.json()
        print(f"case {body['case_id']}: {filename} ({channel}) -> {body['action']} "
              f"(fused_score={body['fused_score']})")
