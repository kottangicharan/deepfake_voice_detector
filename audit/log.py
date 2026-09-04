"""Append-only-ish SQLite decision log. Only /score and end-of-WS-call get recorded — a row is
never rewritten except its three review columns (analyst_override, case_note, reviewed_at)."""
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from risk.types import Decision

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "audit.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id                   TEXT NOT NULL,
    timestamp                 TEXT NOT NULL,
    claimed_channel           TEXT NOT NULL,
    audio_ref                 TEXT,
    signals_json              TEXT NOT NULL,
    spoof_timeline_json       TEXT,
    fused_score                REAL,
    fused_confidence           REAL NOT NULL,
    action                     TEXT NOT NULL,
    abstain                    INTEGER NOT NULL,
    reason                     TEXT NOT NULL,
    degraded                   INTEGER NOT NULL,
    degradation_reasons_json   TEXT NOT NULL,
    threshold_version          TEXT NOT NULL,
    model_versions_json        TEXT NOT NULL,
    analyst_override           TEXT,
    case_note                  TEXT,
    reviewed_at                TEXT
);
CREATE INDEX IF NOT EXISTS idx_decisions_call_id ON decisions(call_id);
CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON decisions(timestamp);
"""


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def record(conn: sqlite3.Connection, decision: Decision, audio_ref: str | None = None) -> int:
    signals_json = json.dumps({k: asdict(v) for k, v in decision.signals.items()})
    cur = conn.execute(
        """INSERT INTO decisions (
            call_id, timestamp, claimed_channel, audio_ref, signals_json, spoof_timeline_json,
            fused_score, fused_confidence, action, abstain, reason, degraded,
            degradation_reasons_json, threshold_version, model_versions_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            decision.call_id, decision.timestamp, decision.claimed_channel, audio_ref,
            signals_json, json.dumps(decision.spoof_timeline),
            decision.fused_score, decision.fused_confidence, decision.action, int(decision.abstain),
            decision.reason, int(decision.degraded), json.dumps(decision.degradation_reasons),
            decision.threshold_version, json.dumps(decision.model_versions),
        ),
    )
    conn.commit()
    return cur.lastrowid


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["signals"] = json.loads(d.pop("signals_json"))
    d["spoof_timeline"] = json.loads(d.pop("spoof_timeline_json") or "null")
    d["degradation_reasons"] = json.loads(d.pop("degradation_reasons_json"))
    d["model_versions"] = json.loads(d.pop("model_versions_json"))
    d["abstain"] = bool(d["abstain"])
    d["degraded"] = bool(d["degraded"])
    return d


def get_case(conn: sqlite3.Connection, case_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM decisions WHERE id = ?", (case_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_cases(conn: sqlite3.Connection, limit: int = 50, offset: int = 0,
                action: str | None = None) -> tuple[list[dict], int]:
    where = "WHERE action = ?" if action else ""
    params = (action,) if action else ()
    total = conn.execute(f"SELECT COUNT(*) FROM decisions {where}", params).fetchone()[0]
    rows = conn.execute(
        f"""SELECT id, call_id, timestamp, claimed_channel, fused_score, fused_confidence,
                   action, abstain, degraded
            FROM decisions {where} ORDER BY id DESC LIMIT ? OFFSET ?""",
        (*params, limit, offset),
    ).fetchall()
    return [dict(r) | {"abstain": bool(r["abstain"]), "degraded": bool(r["degraded"])} for r in rows], total


def review(conn: sqlite3.Connection, case_id: int, analyst_override: str, case_note: str | None) -> dict | None:
    from datetime import datetime, timezone

    cur = conn.execute(
        "UPDATE decisions SET analyst_override = ?, case_note = ?, reviewed_at = ? WHERE id = ?",
        (analyst_override, case_note, datetime.now(timezone.utc).isoformat(), case_id),
    )
    conn.commit()
    if cur.rowcount == 0:
        return None
    return get_case(conn, case_id)
