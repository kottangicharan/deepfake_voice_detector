# Phase 1 — what broke

## fairseq install failed (three separate reasons, in order hit)
Nes2Net_ASVspoof_ITW (the spec's designated day-1 repo) needs fairseq pinned to
commit `a54021305d6b3c4c5959ac9395135f63202db8f1`, plus a fairseq-hosted
wav2vec2 XLSR-300M checkpoint (~1.2GB) and its own checkpoint from Google Drive.
Installed Python 3.11 specifically for this (3.14, the machine default, would
have failed immediately — fairseq's setup.py needs `distutils`, removed in
3.12+). Even on 3.11:

1. **Windows symlink privilege.** `setup.py` calls `os.symlink(examples, fairseq/examples)`
   to satisfy `package_data`; this account lacks `SeCreateSymbolicLinkPrivilege`.
   Worked around by pre-populating `fairseq/examples` as a real copy — the
   symlink call is skipped when the target already exists.
2. **Missing MSVC Build Tools.** fairseq compiles several C++ extensions
   (`libbleu`, `libnat`, ngram-blocking) that need `cl.exe`, not installed here.
   None of them are used by wav2vec2 inference. Worked around via fairseq's own
   `READTHEDOCS=1` env var, which its setup.py already uses to skip
   `ext_modules` entirely when building docs.
3. **Python 3.11 dataclass strictness.** fairseq's own config classes use
   `field: Config = Config()` (a dataclass instance as a mutable default).
   Python 3.11 rejects this outright (`ValueError: mutable default ... use
   default_factory`), and it recurs through dozens of fairseq's config
   classes — not a one-line fix. This same pattern in fairseq's `hydra-core`
   dependency also broke pytest's plugin autoloading in the venv until
   `fairseq`/`hydra-core`/`omegaconf` were uninstalled.

**Fell back to the spec's own designated CPU fallback, `RawTFNet-Pytorch`**:
pure PyTorch, no fairseq, checkpoint bundled in the repo (`ckpts/Best_RawTFNet_32.pth`).
`spoof/scorer.py` wraps it behind `score(waveform, sr) -> float` so nothing
downstream needs to know which backend is running.

## Two smaller snags in the wrapper itself
- `TfSepNet.forward()` calls `.squeeze()` on its output, which drops the batch
  dimension entirely at batch_size=1. `scorer.py` reshapes to `(-1, 2)` before
  softmax to compensate.
- `torchaudio.load()` in this torch/torchaudio combo requires an optional
  `torchcodec` dependency that isn't installed. Switched `audio/preprocess.py`'s
  file loader to `soundfile` instead (already a dependency, no extra install).

## One honest result, not a bug
Scoring a real bona fide LibriSpeech clip (`librosa.example("libri1")`)
currently returns ~0.9998 spoof risk — confidently wrong. RawTFNet-Pytorch's
bundled checkpoint has no calibration or domain adaptation applied here; this
is exactly what Phase 2's eval grid and cost model exist to quantify honestly,
not something to patch away in Phase 1.
