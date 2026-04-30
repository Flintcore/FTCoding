"""Local SQLite storage for user preferences and learned patterns."""
from __future__ import annotations
import sqlite3
import json
from datetime import datetime
from typing import Optional, Any
from pathlib import Path


class MemoryStore:
    """SQLite-based memory store for user preferences and project patterns."""

    def __init__(self, db_path: str = ".ftcoding/memory.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._init_tables()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_tables(self) -> None:
        """Create tables if they don't exist."""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    context TEXT,
                    success BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def record_preference(self, key: str, value: str) -> None:
        """Record or update a user preference."""
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO preferences (key, value, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                   value=excluded.value, updated_at=excluded.updated_at""",
                (key, value, datetime.now().isoformat())
            )
            conn.commit()

    def get_preference(self, key: str) -> Optional[str]:
        """Get a user preference."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT value FROM preferences WHERE key = ?",
                (key,)
            ).fetchone()
            return row["value"] if row else None

    def get_all_preferences(self) -> dict[str, str]:
        """Get all user preferences."""
        with self._get_conn() as conn:
            rows = conn.execute("SELECT key, value FROM preferences").fetchall()
            return {row["key"]: row["value"] for row in rows}

    def record_interaction(
        self,
        command: str,
        context: Optional[str] = None,
        success: bool = True
    ) -> None:
        """Record an interaction for learning."""
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO interactions (command, context, success) VALUES (?, ?, ?)",
                (command, context, success)
            )
            conn.commit()

    def get_recent_interactions(self, limit: int = 10) -> list[dict]:
        """Get recent interaction history."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT command, context, success, created_at
                   FROM interactions ORDER BY created_at DESC LIMIT ?""",
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    def learn_pattern(self, category: str, pattern: str) -> None:
        """Learn or reinforce a pattern."""
        with self._get_conn() as conn:
            existing = conn.execute(
                "SELECT id, frequency FROM patterns WHERE category = ? AND pattern = ?",
                (category, pattern)
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE patterns SET frequency = frequency + 1, updated_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), existing["id"])
                )
            else:
                conn.execute(
                    "INSERT INTO patterns (category, pattern) VALUES (?, ?)",
                    (category, pattern)
                )
            conn.commit()

    def get_patterns(self, category: Optional[str] = None) -> list[dict]:
        """Get learned patterns, optionally filtered by category."""
        with self._get_conn() as conn:
            if category:
                rows = conn.execute(
                    "SELECT * FROM patterns WHERE category = ? ORDER BY frequency DESC",
                    (category,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM patterns ORDER BY frequency DESC"
                ).fetchall()
            return [dict(row) for row in rows]

    def set_knowledge(self, key: str, value: Any) -> None:
        """Store project knowledge."""
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO project_knowledge (key, value, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                   value=excluded.value, updated_at=excluded.updated_at""",
                (key, json.dumps(value), datetime.now().isoformat())
            )
            conn.commit()

    def get_knowledge(self, key: str) -> Optional[Any]:
        """Get project knowledge."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT value FROM project_knowledge WHERE key = ?",
                (key,)
            ).fetchone()
            return json.loads(row["value"]) if row else None
