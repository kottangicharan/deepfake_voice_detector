import sqlite3
import struct

import pytest
import soundfile as sf
from fastapi.testclient import TestClient

import api.main as api_main
from audit import enrollment_store


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch):
    """Every test gets its own in-memory DB — never touches the real audit.db."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    from audit.log import _SCHEMA

    conn.executescript(_SCHEMA)
    conn.commit()
    enrollment_store.ensure_schema(conn)
    monkeypatch.setattr(api_main, "_conn", conn)
    return conn


@pytest.fixture
def client():
    return TestClient(api_main.app)


@pytest.fixture
def audio_file(tmp_path, real_speech):
    waveform, sr = real_speech
    path = tmp_path / "clip.wav"
    sf.write(str(path), waveform, sr)
    return path


def test_score_endpoint_returns_full_decision(client, audio_file):
    with open(audio_file, "rb") as f:
        resp = client.post("/score", files={"audio": ("clip.wav", f, "audio/wav")},
                            data={"claimed_channel": "app"})
    assert resp.status_code == 200
    body = resp.json()
    assert "case_id" in body
    assert body["action"] in ("allow", "step_up", "block_and_review")
    assert body["claimed_channel"] == "app"
    assert body["spoof_timeline"] is not None


def test_cases_list_and_detail_after_scoring(client, audio_file):
    with open(audio_file, "rb") as f:
        score_resp = client.post("/score", files={"audio": ("clip.wav", f, "audio/wav")})
    case_id = score_resp.json()["case_id"]

    list_resp = client.get("/cases")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1

    detail_resp = client.get(f"/cases/{case_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == case_id


def test_case_detail_missing_returns_404(client):
    resp = client.get("/cases/999")
    assert resp.status_code == 404


def test_case_audio_endpoint_returns_file(client, audio_file):
    with open(audio_file, "rb") as f:
        score_resp = client.post("/score", files={"audio": ("clip.wav", f, "audio/wav")})
    case_id = score_resp.json()["case_id"]

    audio_resp = client.get(f"/cases/{case_id}/audio")
    assert audio_resp.status_code == 200
    assert len(audio_resp.content) > 0


def test_review_endpoint_updates_case(client, audio_file):
    with open(audio_file, "rb") as f:
        score_resp = client.post("/score", files={"audio": ("clip.wav", f, "audio/wav")})
    case_id = score_resp.json()["case_id"]

    review_resp = client.post(f"/cases/{case_id}/review",
                               data={"analyst_action": "block_and_review", "note": "confirmed fraud"})
    assert review_resp.status_code == 200
    body = review_resp.json()
    assert body["analyst_override"] == "block_and_review"
    assert body["case_note"] == "confirmed fraud"


def test_review_endpoint_rejects_invalid_action(client, audio_file):
    with open(audio_file, "rb") as f:
        score_resp = client.post("/score", files={"audio": ("clip.wav", f, "audio/wav")})
    case_id = score_resp.json()["case_id"]

    resp = client.post(f"/cases/{case_id}/review", data={"analyst_action": "not_a_real_action"})
    assert resp.status_code == 400


def test_enroll_then_score_uses_voiceprint_signal(client, audio_file):
    with open(audio_file, "rb") as f:
        enroll_resp = client.post("/enroll", data={"owner_id": "merchant-1"},
                                   files={"audio": ("clip.wav", f, "audio/wav")})
    assert enroll_resp.status_code == 200

    with open(audio_file, "rb") as f:
        score_resp = client.post("/score", files={"audio": ("clip.wav", f, "audio/wav")},
                                  data={"owner_id": "merchant-1"})
    body = score_resp.json()
    assert body["signals"]["voiceprint"]["score"] is not None


def test_stream_websocket_emits_score_updates_and_records_a_case(client, real_speech):
    waveform, sr = real_speech
    import numpy as np
    import torchaudio
    import torch

    wav16k = torchaudio.functional.resample(torch.as_tensor(waveform, dtype=torch.float32), sr, 16000).numpy()
    pcm16 = (np.clip(wav16k, -1.0, 1.0) * 32767).astype(np.int16)

    with client.websocket_connect("/stream") as ws:
        ws.send_text('{"claimed_channel": "pstn"}')
        chunk_samples = 4000  # 250ms @ 16kHz
        got_update = False
        for start in range(0, len(pcm16), chunk_samples):
            ws.send_bytes(pcm16[start:start + chunk_samples].tobytes())
            if start >= 16000:  # after ~1s of audio, expect an update
                msg = ws.receive_json()
                assert msg["type"] == "score_update"
                got_update = True
                break
        assert got_update
        ws.send_text('{"type": "end_call"}')

    list_resp = client.get("/cases")
    assert list_resp.json()["total"] == 1
