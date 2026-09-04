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
| ASVspoof2019 LA (eval) | download in progress (redownloading after repeated MD5 corruption from the host) | pending | pending |
| ASVspoof2021 DF (eval) | download in progress (3 of 4 parts verified, last part in flight) | pending | pending |
| In-the-Wild | 7,860 / 31,779 scored so far (run ongoing) | **~37.0%** (preliminary, partial) | pending |
| IndieFake | not run — gated behind a manual research-access request form, no bulk download found | — | — |

Preliminary In-the-Wild EER lands at threshold≈1.0000 — the model's scores are so heavily
saturated toward "spoof" that even the maximum possible threshold barely separates the classes.
This matches the Phase 1 finding (a real bona-fide clip scored ~99.98% spoof risk): the
uncalibrated RawTFNet fallback is close to useless on real-world audio as-is. Expect this number
to move as the run completes, but not by much given how consistent it's been across thousands of
trials already.

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
