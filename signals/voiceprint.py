"""Speaker verification: enroll a reference clip per account owner, cosine-compare at call time.

Expect this to be fooled by a good voice clone on its own — a clone is built to pass exactly this
kind of check. That's exactly why it isn't the only signal in the fusion: it answers "does this
sound like the enrolled owner", never "is this synthetic".
"""
import numpy as np
import torch

_model = None


def _get_model():
    global _model
    if _model is None:
        from speechbrain.inference.speaker import EncoderClassifier
        from speechbrain.utils.fetching import LocalStrategy

        _model = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="third_party/spkrec-ecapa-voxceleb",
            local_strategy=LocalStrategy.COPY,  # symlinks need a Windows privilege this account lacks
        )
    return _model


def enroll(waveform: np.ndarray, sr: int) -> np.ndarray:
    """Returns a speaker embedding for a 16kHz reference clip, to be stored per account owner."""
    if sr != 16000:
        raise ValueError(f"expected 16kHz audio, got {sr}Hz — run audio.preprocess first")
    wav = torch.as_tensor(waveform, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        embedding = _get_model().encode_batch(wav)
    return embedding.squeeze().numpy()


def verify(waveform: np.ndarray, sr: int, enrolled_embedding: np.ndarray) -> dict:
    """Returns {score, reason, confidence}. score in [0, 1], higher = more likely NOT the enrolled owner."""
    call_embedding = enroll(waveform, sr)
    cos_sim = float(
        np.dot(call_embedding, enrolled_embedding)
        / (np.linalg.norm(call_embedding) * np.linalg.norm(enrolled_embedding) + 1e-9)
    )
    mismatch_score = float(np.clip((1 - cos_sim) / 2, 0.0, 1.0))
    confidence = float(np.clip(abs(cos_sim), 0.0, 1.0))

    if mismatch_score < 0.3:
        reason = f"voiceprint matches enrolled owner (cosine similarity {cos_sim:.3f})"
    elif mismatch_score < 0.6:
        reason = f"voiceprint partially matches enrolled owner (cosine similarity {cos_sim:.3f}) — inconclusive"
    else:
        reason = f"voiceprint does not match enrolled owner (cosine similarity {cos_sim:.3f})"

    return {"score": mismatch_score, "reason": reason, "confidence": confidence}
