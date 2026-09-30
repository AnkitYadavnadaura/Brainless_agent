"""Durable metadata-only storage for generic browser tabs."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from time import time
from urllib.parse import urlsplit


class BrowserSessionStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS browser_tabs (
                    session_id TEXT NOT NULL,
                    browser_id TEXT NOT NULL DEFAULT '',
                    tab_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    site TEXT NOT NULL DEFAULT '',
                    state TEXT NOT NULL,
                    last_action TEXT NOT NULL,
                    checkpoint TEXT NOT NULL,
                    updated REAL NOT NULL,
                    PRIMARY KEY (session_id, tab_id)
                )
            """)
            columns = {row[1] for row in connection.execute(
                "PRAGMA table_info(browser_tabs)")}
            if "browser_id" not in columns:
                connection.execute(
                    "ALTER TABLE browser_tabs ADD COLUMN browser_id TEXT NOT NULL DEFAULT ''")
            if "site" not in columns:
                connection.execute(
                    "ALTER TABLE browser_tabs ADD COLUMN site TEXT NOT NULL DEFAULT ''")

    def save_tab(self, session_id: str, tab_id: str, url: str, title: str,
                 state: str, last_action: str,
                 checkpoint: dict[str, str] | None = None,
                 browser_id: str = "") -> None:
        parts = urlsplit(url)
        if (parts.scheme != "https" or not parts.hostname
                or parts.username is not None or parts.password is not None
                or parts.port not in (None, 443)):
            raise ValueError("Only credential-free HTTPS tab URLs can be persisted")
        with sqlite3.connect(self.path) as connection:
            connection.execute("""
                INSERT INTO browser_tabs
                    (session_id, browser_id, tab_id, url, title, site, state,
                     last_action, checkpoint, updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, tab_id) DO UPDATE SET
                    browser_id=excluded.browser_id, url=excluded.url,
                    title=excluded.title, site=excluded.site, state=excluded.state,
                    last_action=excluded.last_action, checkpoint=excluded.checkpoint,
                    updated=excluded.updated
            """, (session_id, browser_id, tab_id, url, title[:500],
                  parts.hostname or "", state, last_action,
                  json.dumps(checkpoint or {}, ensure_ascii=True), time()))

    def tabs(self, session_id: str) -> list[dict[str, str]]:
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute("""
                SELECT browser_id, tab_id, url, title, site, state, last_action, checkpoint
                FROM browser_tabs WHERE session_id=? ORDER BY updated, tab_id
            """, (session_id,)).fetchall()
        return [{
            "browser_id": row[0], "tab_id": row[1], "url": row[2],
            "title": row[3], "site": row[4], "state": row[5],
            "last_action": row[6], "checkpoint": row[7],
        } for row in rows]

    def remove_tab(self, session_id: str, tab_id: str) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "DELETE FROM browser_tabs WHERE session_id=? AND tab_id=?",
                (session_id, tab_id))

    def close(self) -> None:
        return None
