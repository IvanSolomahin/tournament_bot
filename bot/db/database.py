from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from typing import Any, Iterable


SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class Database:
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._lock = asyncio.Lock()

    def init_schema(self) -> None:
        self._conn.executescript(SCHEMA_PATH.read_text())
        self._conn.commit()

    async def execute(self, query: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        async with self._lock:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._execute_sync, query, params
            )

    def _execute_sync(self, query: str, params: Iterable[Any]) -> sqlite3.Cursor:
        cur = self._conn.execute(query, params)
        self._conn.commit()
        return cur

    async def fetchone(self, query: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
        async with self._lock:
            return await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._conn.execute(query, params).fetchone()
            )

    async def fetchall(self, query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        async with self._lock:
            return await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._conn.execute(query, params).fetchall()
            )

    def close(self) -> None:
        self._conn.close()
