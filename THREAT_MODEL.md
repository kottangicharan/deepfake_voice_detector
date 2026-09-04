# Threat Model

## The loss class this defends

**Unauthorized settlement-account / payout-detail changes made over a voice support channel
using a cloned voice.** An attacker with a short sample of a merchant's or account owner's real
voice (a few seconds is enough with current commercial cloning tools) calls support, impersonates
the owner, and talks a human agent into redirecting where money settles. The loss isn't the phone
call — it's every subsequent payout that lands in the attacker's account until someone notices.

## Attack path

1. Attacker obtains a voice sample of the account owner (public video, a prior recorded call, a
   voicemail — sourcing is out of scope for this system; assume it happens).
2. Attacker clones the voice with any commercial or open-source TTS/voice-conversion tool.
3. Attacker calls support, claims to be the account owner, requests a settlement-account change.
4. A human agent, working from voice alone plus whatever the attacker can answer about the
   account, authorizes the change.
5. Funds that would have settled to the real owner now settle to the attacker.

Step 4 is the single point of failure this system targets: **voice is currently sole
authorization** for a request that moves money. The fix is not "detect the clone perfectly" — no
model does, see below — it's removing voice as sole authorization for this specific request class.

## What this system catches

- A synthetic or heavily-processed voice on the call, via `spoof/scorer.py` — imperfectly (see
  `docs/METRICS.md`; the honest EER numbers are the point, not a claimed high accuracy).
- A voice that doesn't match the enrolled account owner, via `signals/voiceprint.py` — again
  imperfectly; a good clone is built specifically to pass a speaker-verification check, so this
  signal is deliberately never trusted alone.
- A call whose acoustic bandwidth doesn't match its claimed path (e.g. claims to be a landline
  call but shows full-band audio, suggesting injected/played audio rather than a live mic over
  that path), via `signals/channel.py`.
- A pipeline failure (model crash, OOM, unavailable weights, insufficient audio) is designed to
  **degrade closed**: `risk/degradation.py` turns any signal failure into "exclude this signal and
  lean toward friction," never into a silent allow. See `risk/policy.py`'s abstain band and the
  `degraded` flag on every decision.

## What this system does NOT catch, and does not try to

- **A well-executed clone will likely pass all four signals.** This is stated plainly, not
  hedged: `docs/METRICS.md` shows the shipped model's raw scores are badly saturated even on
  bona-fide audio, and even a well-calibrated commercial detector's published numbers move from
  ~1-2% EER in lab conditions to 20%+ on real-world audio (see the original spec's own framing).
  Nobody should read a low risk score from this system as proof a caller is who they claim.
- **Everything upstream of the call**: how the attacker got the voice sample, account
  reconnaissance, social engineering of the agent on non-voice details. Out of scope.
- **Non-voice channels**: email, chat, in-app requests. This system only ever sees a voice call.
- **`signals/intent.py` does not exist in this repo** — it needs an LLM API key that hasn't been
  provided. Until it's wired in, the "does this request sound like an account-change attempt"
  signal that's supposed to escalate regardless of the other three simply isn't running. The
  fusion and policy code (`risk/fusion.py`, `risk/policy.py`) already accept an absent intent
  signal gracefully rather than pretending it ran.

## Why detection alone doesn't close the loss class — the actual protection

The model buys detection and lower friction on the common case. The **protection** is the policy
layer, not the model:

- A sensitive request (settlement-account change) triggers a mandatory **out-of-band step-up**
  (verify through a channel the attacker doesn't control) regardless of how confident the model
  is, once the fused score crosses `step_up` — see `risk/policy.py`.
- A **hold-and-notify window** on any settlement-account change lets the real owner catch and
  reverse a fraudulent change before funds move, independent of whether the call was flagged.
  (This specific hold mechanism is a policy recommendation for the integrating system, not
  something this repo implements — this repo's job stops at the risk decision and audit record.)
- Every decision is written to an **append-only audit log** (`audit/log.py`) — inputs, every
  signal score, threshold version, model version, and any analyst override — so a missed case is
  reconstructable after the fact, not lost.

In short: **voice is never sole authorization for a settlement-account change.** This system makes
that policy cheap to enforce (most calls get through with no friction) rather than replacing it.

## No generation capability

This repository contains no code that synthesizes, clones, or otherwise generates speech. Every
model here is a discriminator (spoof detection, speaker verification) or a signal-processing
routine (channel analysis). `audio/telephony.py` simulates telephony *degradation* (codec,
packet loss, noise) for evaluation purposes only — it processes existing recorded audio, it does
not synthesize a voice from text or from another speaker's voice. No text-to-speech, voice
conversion, or voice cloning library is imported or vendored anywhere in this repo. See
`docs/WHAT_BROKE.md` for the one adjacent decision this constrains: the spec's originally-named
reference implementation could not be installed, and the fallback chosen (RawTFNet-Pytorch) was
selected in part because it is, like every other model in this repo, detection-only.
