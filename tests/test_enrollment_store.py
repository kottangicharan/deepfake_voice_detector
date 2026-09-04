import sqlite3

import numpy as np

from audit.enrollment_store import get_enrollment, save_enrollment


def _connection():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def test_save_and_get_enrollment_roundtrip():
    conn = _connection()
    embedding = np.random.default_rng(0).normal(0, 1, size=192).astype(np.float32)
    save_enrollment(conn, "merchant-1", embedding)

    loaded = get_enrollment(conn, "merchant-1")
    assert np.allclose(loaded, embedding)


def test_get_enrollment_missing_returns_none():
    conn = _connection()
    assert get_enrollment(conn, "nobody") is None


def test_save_enrollment_overwrites_existing():
    conn = _connection()
    save_enrollment(conn, "merchant-1", np.zeros(192, dtype=np.float32))
    new_embedding = np.ones(192, dtype=np.float32)
    save_enrollment(conn, "merchant-1", new_embedding)

    loaded = get_enrollment(conn, "merchant-1")
    assert np.allclose(loaded, new_embedding)
