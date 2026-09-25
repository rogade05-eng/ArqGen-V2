"""SQLite connection management and session/transaction helpers (spec 78)."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from core.errors import PersistenceError


class ConnectionManager:
    """Opens SQLite databases with the project's professional settings."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        directory = os.path.dirname(os.path.abspath(self.db_path))
        if directory:
            os.makedirs(directory, exist_ok=True)
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = FULL")
            return conn
        except sqlite3.Error as exc:
            raise PersistenceError(
                message=f"No se pudo abrir la base de datos: {self.db_path}",
                code="ARQ-PER-002",
                context={"path": self.db_path, "detail": str(exc)},
                suggested_action="Verifique permisos de escritura en la carpeta del proyecto.",
            ) from exc

    @staticmethod
    def integrity_check(conn: sqlite3.Connection) -> str:
        row = conn.execute("PRAGMA integrity_check").fetchone()
        return str(row[0]) if row else "unknown"


class Session:
    """Transaction-scoped access to one SQLite connection."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        try:
            return self.conn.execute(sql, params)
        except sqlite3.Error as exc:
            raise PersistenceError(
                message=f"Error SQL: {exc}",
                code="ARQ-PER-003",
                context={"sql": sql[:200]},
            ) from exc

    def query_all(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self.execute(sql, params).fetchall()

    def query_one(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        return self.execute(sql, params).fetchone()

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def close(self) -> None:
        try:
            self.conn.close()
        except sqlite3.Error:  # pragma: no cover
            pass


@contextmanager
def transaction(session: Session) -> Iterator[Session]:
    """All-or-nothing block: commit on success, rollback on exception."""
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise


def json_dumps(value: Any) -> str:
    import json
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def json_loads(value: Optional[str], default: Any = None) -> Any:
    import json
    if value is None or value == "":
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


__all__ = ["ConnectionManager", "Session", "transaction", "json_dumps", "json_loads"]
