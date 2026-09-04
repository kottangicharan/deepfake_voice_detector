# Phase 2 — Evaluation

Model under test: `spoof/scorer.py` (RawTFNet-Pytorch, see [WHAT_BROKE.md](WHAT_BROKE.md) for why
this replaces the spec's originally-designated Nes2Net_ASVspoof_ITW). No calibration applied yet —
these are raw model scores.

**Scoring throughput note:** CPU-only scoring runs at ~1,000 trials/hour (VAD + model forward
pass + file I/O per clip). In-the-Wild's 31,779 trials are scored in full (already in progress
when this was measured, so it kept running to completion). LA's 71,237 (~3 days at this rate) and
DF's 533,928 (~3 weeks) both instead use a 5,000-trial stratified random subsample
(`eval.protocols.subsample_trials`, preserving the bonafide/spoof ratio) for a fast, honest EER
estimate. The full datasets are downloaded regardless — nothing stops a full-set run later given
more compute time/budget.

## EER by dataset and condition

| Dataset | Trials | Clean EER | Telephony EER |
|---|---|---|---|
| ASVspoof2019 LA (eval) | 5,000 (stratified subsample of 71,237) | **24.43%** | pending |
| ASVspoof2021 DF (eval) | 5,000 (stratified subsample of 533,928) | **re-scoring** (a decode fallback bug fix invalidated the first run, see below) | pending |
| In-the-Wild | ~25,000 / 31,779 scored so far (run ongoing) | **~37%** (moving as the run completes) | pending |
| IndieFake | not run — gated behind a manual research-access request form, no bulk download found | — | — |

All three shipped model scores are heavily saturated toward "spoof" even on bona-fide audio (a
real clip scored ~99.98% spoof risk in Phase 1) — these EER numbers, not a claimed accuracy
figure, are the honest result of an uncalibrated CPU fallback model on real-world audio.

**A real bug found via this eval, not hidden:** the first DF run had 2,166/5,000 trials (43%)
fail to decode with libsndfile errors ("unknown error in flac decoder", "flac decoder lost
sync") despite the flac files being structurally valid — confirmed via a correct `fLaC` header
and a clean `ffprobe` read on multiple sampled failures. `audio/preprocess.py`'s `load_audio` now
falls back to librosa's audioread/ffmpeg backend when soundfile's libFLAC fails, fixing what was
about to become a silently-shrunk, less-statistically-valid DF sample. LA had zero decode
failures — this is specific to something about how a portion of DF's flacs were encoded, not a
general problem with the pipeline.

DET curves: `docs/det_<dataset>_<condition>.png` (generated per run).

## Cost model

`expected_cost(threshold) = P(false_accept) * fraud_loss + P(false_reject) * support_cost`

**Assumptions** (illustrative, not measured — swap in real figures if available):
- `fraud_loss` = ₹50,000 — average loss from a successful settlement-account takeover pushed through on a cloned voice
- `support_cost` = ₹150 — cost of one step-up/support friction event for a legitimate caller wrongly flagged

Chosen operating point, precision/recall at that point, and the cost-vs-threshold curve
(`docs/cost_curve.png`) go here once real scores exist.

## Where this fails

To be filled in once real numbers land — this section is the point of Phase 2, not an
afterthought.
