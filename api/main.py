"""FastAPI service: POST /score, GET /cases, GET /cases/{id}, GET /cases/{id}/audio,
POST /cases/{id}/review, POST /enroll, WS /stream.

CORS is wide open (allow_origins=["*"]) — fine for a local buildathon demo, not a production
posture; a deliberate simplification, noted rather than silently shipped.
"""
import json
import tempfile
import uuid
from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from audio.preprocess import load_audio
from audit import enrollment_store, log as audit_log
from risk.fusion import decide
from signals.voiceprint import enroll as voiceprint_enroll

REFRESH_INTERVAL_SEC = 1.0  # measured: decide() runs in ~17ms on this machine, well under budget
ROLLING_WINDOW_SEC = 3.5
EMA_ALPHA = 0.4

AUDIO_STORE = Path(__file__).resolve().parent.parent / "audit" / "audio_store"
AUDIO_STORE.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Voice Risk Layer")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_conn = audit_log.get_connection()
enrollment_store.ensure_schema(_conn)


@app.post("/enroll")
async def enroll_endpoint(owner_id: str = Form(...), audio: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    from audio.preprocess import preprocess

    waveform, sr = load_audio(tmp_path)
    clean = preprocess(waveform, sr)
    if clean is None:
        raise HTTPException(400, "under 1.5s of usable speech survived VAD")

    embedding = voiceprint_enroll(clean, 16000)
    enrollment_store.save_enrollment(_conn, owner_id, embedding)
    return {"owner_id": owner_id, "enrolled_at": "now"}


@app.post("/score")
async def score_endpoint(audio: UploadFile = File(...), claimed_channel: str = Form("unknown"),
                          owner_id: str | None = Form(None)):
    call_id = str(uuid.uuid4())
    audio_bytes = await audio.read()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    waveform, sr = load_audio(tmp_path)

    enrolled_embedding = enrollment_store.get_enrollment(_conn, owner_id) if owner_id else None
    decision = decide(waveform, sr, call_id=call_id, claimed_channel=claimed_channel,
                       enrolled_embedding=enrolled_embedding)

    audio_ref = AUDIO_STORE / f"{call_id}.wav"
    sf.write(str(audio_ref), waveform, sr)
    case_id = audit_log.record(_conn, decision, audio_ref=str(audio_ref))

    return {"case_id": case_id, **decision.to_dict()}


@app.get("/cases")
def list_cases_endpoint(limit: int = 50, offset: int = 0, action: str | None = None):
    rows, total = audit_log.list_cases(_conn, limit=limit, offset=offset, action=action)
    return {"cases": rows, "total": total}


@app.get("/cases/{case_id}")
def get_case_endpoint(case_id: int):
    case = audit_log.get_case(_conn, case_id)
    if case is None:
        raise HTTPException(404, "case not found")
    return case


@app.get("/cases/{case_id}/audio")
def get_case_audio_endpoint(case_id: int):
    case = audit_log.get_case(_conn, case_id)
    if case is None or not case.get("audio_ref"):
        raise HTTPException(404, "no audio for this case")
    return FileResponse(case["audio_ref"])


@app.post("/cases/{case_id}/review")
def review_case_endpoint(case_id: int, analyst_action: str = Form(...), note: str = Form("")):
    if analyst_action not in ("allow", "step_up", "block_and_review"):
        raise HTTPException(400, "analyst_action must be allow|step_up|block_and_review")
    updated = audit_log.review(_conn, case_id, analyst_action, note or None)
    if updated is None:
        raise HTTPException(404, "case not found")
    return updated


@app.websocket("/stream")
async def stream_endpoint(ws: WebSocket):
    await ws.accept()
    call_id = str(uuid.uuid4())

    handshake = json.loads(await ws.receive_text())
    claimed_channel = handshake.get("claimed_channel", "unknown")
    owner_id = handshake.get("owner_id")
    enrolled_embedding = enrollment_store.get_enrollment(_conn, owner_id) if owner_id else None

    sr = 16000
    max_samples = int(ROLLING_WINDOW_SEC * sr)
    buffer = np.zeros(0, dtype=np.float32)
    smoothed_score = None

    try:
        while True:
            try:
                message = await ws.receive()
            except WebSocketDisconnect:
                break

            if message.get("type") == "websocket.disconnect":
                break

            if "text" in message and message["text"] is not None:
                payload = json.loads(message["text"])
                if payload.get("type") == "end_call":
                    break
                continue

            if "bytes" in message and message["bytes"] is not None:
                chunk = np.frombuffer(message["bytes"], dtype=np.int16).astype(np.float32) / 32768.0
                buffer = np.concatenate([buffer, chunk])[-max_samples:]

                if len(buffer) >= sr:  # wait for at least 1s before scoring
                    decision = decide(buffer, sr, call_id=call_id, claimed_channel=claimed_channel,
                                       enrolled_embedding=enrolled_embedding, compute_timeline=False)
                    if decision.fused_score is not None:
                        smoothed_score = (decision.fused_score if smoothed_score is None
                                           else EMA_ALPHA * decision.fused_score + (1 - EMA_ALPHA) * smoothed_score)
                    await ws.send_json({
                        "type": "score_update",
                        "fused_score": decision.fused_score,
                        "fused_confidence": decision.fused_confidence,
                        "action": decision.action,
                        "abstain": decision.abstain,
                        "signals": {k: {"score": v.score, "reason": v.reason} for k, v in decision.signals.items()},
                        "smoothed_score": smoothed_score,
                    })
    finally:
        if len(buffer) > 0:
            final_decision = decide(buffer, sr, call_id=call_id, claimed_channel=claimed_channel,
                                     enrolled_embedding=enrolled_embedding, compute_timeline=True)
            audio_ref = AUDIO_STORE / f"{call_id}.wav"
            sf.write(str(audio_ref), buffer, sr)
            audit_log.record(_conn, final_decision, audio_ref=str(audio_ref))
        try:
            await ws.close()
        except RuntimeError:
            pass
