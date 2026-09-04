# Voice Risk Layer

Razorpay AI Buildathon, Track 02 — AI Risk Manager.

## The problem

A cloned voice, a few seconds of source audio, and one phone call to support is enough to redirect
where a merchant's settlement payouts land. Every payout after that call — not the call itself —
is the loss, until someone notices. **Voice is currently sole authorization** for a request class
that moves real money, and no detector, including this one, is good enough to change that on its
own (see [METRICS](docs/METRICS.md): the shipped model's raw scores are badly saturated even on
real bona-fide audio). At an illustrative ₹50,000 average loss per successful takeover — the
figure this repo's cost model uses, see below — the fix isn't a better classifier, it's making
"never trust voice alone for this request" cheap enough to actually enforce. That's what this
repo builds. Full attack path and what is/isn't caught: [THREAT_MODEL.md](THREAT_MODEL.md).

## Architecture

```
Call audio (file upload or live mic stream)
       │
   audio/preprocess.py   resample → 16kHz → VAD-trim → normalize
   (< 1.5s usable speech → ABSTAIN, never a guess)
       │
       ├── spoof/scorer.py       — synthetic-speech score
       ├── signals/channel.py    — claimed call path vs actual spectral bandwidth
       ├── signals/voiceprint.py — match vs the enrolled account owner
       └── signals/intent.py     — not built; needs an LLM API key not yet provided
       │
   risk/fusion.py     rescale (spoof score is saturated raw) + weighted blend
   risk/policy.py     → allow | step_up | block_and_review, + abstain band
   risk/degradation.py  any signal failure degrades closed, never fails open
       │
   audit/log.py        every decision, append-only, SQLite
       │
   api/main.py (FastAPI)
       POST /score        one-shot: upload a clip, get a full decision
       WS   /stream        live: rolling buffer, re-scored ~1x/sec
       GET  /cases          POST /cases/{id}/review     analyst queue + audit trail
       │
   frontend/  (React + Vite)   case queue, signal cards, risk gauge,
                                waveform colored by real per-window spoof scores,
                                live mic call panel
```

Every module above is independently unit-tested (`tests/`, one file per module, 70+ tests).
`spoof/scorer.py` wraps RawTFNet-Pytorch, not the spec's originally-named reference model — see
[docs/WHAT_BROKE.md](docs/WHAT_BROKE.md) for the three independent reasons that model couldn't be
installed on this machine, and why the fallback is still detection-only, never generation-capable.

## Metrics — the actual submission

The eval grid ([docs/METRICS.md](docs/METRICS.md)) is the point, not a footnote. It scores the
real ASVspoof2019 LA, ASVspoof2021 DF, and In-the-Wild datasets — not synthetic test data — under
both clean and simulated-telephony conditions, and reports EER honestly rather than picking a
flattering number. It also documents a real production incident hit *during this build*: Zenodo's
CDN silently returned wrong-but-correctly-sized bytes for range requests, twice, on the DF
download — caught only because every download here is checksum-verified, not just size-checked.
IndieFake is documented as attempted and blocked (gated behind a manual research-access request,
no bulk download available) rather than silently dropped.

## How to run

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m pytest tests/          # 70+ tests, all independently runnable
.venv\Scripts\python -m uvicorn api.main:app --reload --port 8123   # backend on :8123
cd frontend && npm install && npm run dev       # console on :5173
```

`scripts/seed_demo_cases.py` populates the case queue with real clips before a live demo.
Re-run the eval grid yourself: `python -m eval.harness --format asvspoof --protocol <path>
--audio-dir <path> --out-scores <path> --condition clean` (see `eval/harness.py`'s `--help`
for the full flag set, including `--n-samples` for a subsample and `--condition telephony`).

## What this is not

No code in this repository generates, clones, or synthesizes speech — every model here is a
discriminator. See [THREAT_MODEL.md](THREAT_MODEL.md#no-generation-capability) for the explicit
statement this track requires.
