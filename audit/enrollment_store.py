"""Persistent per-owner voiceprint embeddings, same DB as audit/log.py."""
import sqlite3
from datetime import datetime, timezone

import numpy as np

_SCHEMA = """
CREATE TABLE IF NOT EXISTS enrollments (
    owner_id     TEXT PRIMARY KEY,
    embedding    BLOB NOT NULL,
    enrolled_at  TEXT NOT NULL
);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


def save_enrollment(conn: sqlite3.Connection, owner_id: str, embedding: np.ndarray) -> None:
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO enrollments (owner_id, embedding, enrolled_at) VALUES (?, ?, ?) "
        "ON CONFLICT(owner_id) DO UPDATE SET embedding = excluded.embedding, enrolled_at = excluded.enrolled_at",
        (owner_id, np.asarray(embedding, dtype=np.float32).tobytes(), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def get_enrollment(conn: sqlite3.Connection, owner_id: str) -> np.ndarray | None:
    ensure_schema(conn)
    row = conn.execute("SELECT embedding FROM enrollments WHERE owner_id = ?", (owner_id,)).fetchone()
    if row is None:
        return None
    blob = row[0] if not isinstance(row, sqlite3.Row) else row["embedding"]
    return np.frombuffer(blob, dtype=np.float32)
