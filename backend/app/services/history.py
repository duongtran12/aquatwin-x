import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE = PROJECT_ROOT / "data" / "aquatwin_history.db"


class RunHistoryStore:
    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path).resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._lock, closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS run_history (
                        run_id TEXT PRIMARY KEY,
                        run_type TEXT NOT NULL,
                        network_id TEXT NOT NULL,
                        pipe_id TEXT,
                        runtime_mode TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        summary_json TEXT NOT NULL,
                        result_json TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_run_history_created_at ON run_history(created_at DESC)"
                )

    @staticmethod
    def _metadata(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "run_id": row["run_id"],
            "run_type": row["run_type"],
            "network_id": row["network_id"],
            "pipe_id": row["pipe_id"],
            "runtime_mode": row["runtime_mode"],
            "created_at": row["created_at"],
            "summary": json.loads(row["summary_json"]),
        }

    def save(
        self,
        run_type: str,
        network_id: str,
        pipe_id: str | None,
        runtime_mode: str,
        summary: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        run_id = uuid4().hex
        created_at = datetime.now(UTC).isoformat()
        with self._lock, closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO run_history (
                        run_id, run_type, network_id, pipe_id, runtime_mode,
                        created_at, summary_json, result_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        run_type,
                        network_id,
                        pipe_id,
                        runtime_mode,
                        created_at,
                        json.dumps(summary, ensure_ascii=False),
                        json.dumps(result, ensure_ascii=False),
                    ),
                )
        return {
            "run_id": run_id,
            "run_type": run_type,
            "network_id": network_id,
            "pipe_id": pipe_id,
            "runtime_mode": runtime_mode,
            "created_at": created_at,
            "summary": summary,
        }

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM run_history ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._metadata(row) for row in rows]

    def get(self, run_id: str) -> dict[str, Any]:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM run_history WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise KeyError(run_id)
        return {**self._metadata(row), "result": json.loads(row["result_json"])}
