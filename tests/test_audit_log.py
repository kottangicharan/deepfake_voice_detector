import sqlite3

import pytest

from audit.log import get_case, list_cases, record, review
from risk.types import Decision, SignalResult


def _connection():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    from audit.log import _SCHEMA

    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def _decision(action="allow"):
    return Decision(
        call_id="call-1", timestamp="2026-09-04T00:00:00+00:00", claimed_channel="pstn",
        signals={"spoof": SignalResult(score=0.2, reason="ok", confidence=0.9)},
        fused_score=0.2, fused_confidence=0.9, action=action, abstain=False,
        reason="low risk", degraded=False, degradation_reasons=[],
        threshold_version="v1", model_versions={"spoof": "rawtfnet-32"},
        spoof_timeline=[(0.0, 1.0, 0.2)],
    )


def test_record_and_get_case():
    conn = _connection()
    case_id = record(conn, _decision(), audio_ref="audit/audio_store/call-1.wav")
    case = get_case(conn, case_id)
    assert case["call_id"] == "call-1"
    assert case["action"] == "allow"
    assert case["signals"]["spoof"]["score"] == 0.2
    assert case["spoof_timeline"] == [[0.0, 1.0, 0.2]]
    assert case["audio_ref"] == "audit/audio_store/call-1.wav"


def test_get_case_missing_returns_none():
    conn = _connection()
    assert get_case(conn, 999) is None


def test_list_cases_orders_newest_first_and_filters_by_action():
    conn = _connection()
    id1 = record(conn, _decision(action="allow"))
    id2 = record(conn, _decision(action="block_and_review"))

    rows, total = list_cases(conn)
    assert total == 2
    assert rows[0]["id"] == id2  # newest first

    rows, total = list_cases(conn, action="allow")
    assert total == 1
    assert rows[0]["id"] == id1


def test_review_updates_only_review_columns():
    conn = _connection()
    case_id = record(conn, _decision())
    updated = review(conn, case_id, analyst_override="block_and_review", case_note="looked suspicious")
    assert updated["analyst_override"] == "block_and_review"
    assert updated["case_note"] == "looked suspicious"
    assert updated["reviewed_at"] is not None
    assert updated["action"] == "allow"  # the original policy decision is untouched


def test_review_missing_case_returns_none():
    conn = _connection()
    assert review(conn, 999, "allow", None) is None
