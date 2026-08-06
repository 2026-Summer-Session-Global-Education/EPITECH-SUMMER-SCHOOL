"""Light persistence with the standard-library sqlite3 module.

Stores each analysis (document text plus findings) so there is a history endpoint.
Kept deliberately small: no ORM, no external database to install.
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any


class Store:
    def __init__(self, path: str):
        self.path = path
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT,
                    analyzer TEXT,
                    mode TEXT,
                    created_at REAL,
                    text TEXT,
                    findings_json TEXT,
                    counts_json TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS context_docs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT,
                    created_at REAL,
                    text TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT,
                    key TEXT,
                    provider TEXT DEFAULT 'anthropic',
                    created_at REAL
                )
                """
            )
            # migrate older databases that predate the provider column
            cols = [r["name"] for r in conn.execute("PRAGMA table_info(api_keys)")]
            if "provider" not in cols:
                conn.execute("ALTER TABLE api_keys ADD COLUMN provider TEXT DEFAULT 'anthropic'")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT)"
            )

    def save(self, result: dict[str, Any], text: str) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO analyses (doc_id, analyzer, mode, created_at, text, findings_json, counts_json)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    result["doc_id"],
                    result["analyzer"],
                    result["mode"],
                    time.time(),
                    text,
                    json.dumps(result["findings"]),
                    json.dumps(result["counts"]),
                ),
            )
            return int(cur.lastrowid)

    # ---- API keys (stored locally; masked before leaving the backend) ----

    def add_key(self, label: str, key: str, provider: str = "anthropic") -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO api_keys (label, key, provider, created_at) VALUES (?, ?, ?, ?)",
                (label, key, provider, time.time()),
            )
            return int(cur.lastrowid)

    def list_keys(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, label, key, provider, created_at FROM api_keys ORDER BY id"
            ).fetchall()
        return [{"id": r["id"], "label": r["label"], "key": r["key"],
                 "provider": r["provider"] or "anthropic",
                 "created_at": r["created_at"]} for r in rows]

    def get_key(self, key_id: int) -> dict[str, Any] | None:
        with self._conn() as conn:
            r = conn.execute(
                "SELECT id, label, key, provider FROM api_keys WHERE id = ?", (key_id,)
            ).fetchone()
        return {"id": r["id"], "label": r["label"], "key": r["key"],
                "provider": r["provider"] or "anthropic"} if r else None

    def delete_key(self, key_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))

    # ---- key/value settings ---------------------------------------------

    def get_setting(self, name: str) -> str | None:
        with self._conn() as conn:
            r = conn.execute("SELECT value FROM settings WHERE name = ?", (name,)).fetchone()
        return r["value"] if r else None

    def set_setting(self, name: str, value: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO settings (name, value) VALUES (?, ?) "
                "ON CONFLICT(name) DO UPDATE SET value = excluded.value",
                (name, value),
            )

    def add_context(self, filename: str, text: str) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO context_docs (filename, created_at, text) VALUES (?, ?, ?)",
                (filename, time.time(), text),
            )
            return int(cur.lastrowid)

    def list_context(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, filename, created_at, text FROM context_docs ORDER BY id"
            ).fetchall()
        return [
            {"id": r["id"], "filename": r["filename"],
             "chars": len(r["text"] or ""), "text": r["text"] or ""}
            for r in rows
        ]

    def delete_context(self, doc_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM context_docs WHERE id = ?", (doc_id,))

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, doc_id, analyzer, mode, created_at, counts_json"
                " FROM analyses ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "doc_id": r["doc_id"],
                "analyzer": r["analyzer"],
                "mode": r["mode"],
                "created_at": r["created_at"],
                "counts": json.loads(r["counts_json"]),
            }
            for r in rows
        ]
