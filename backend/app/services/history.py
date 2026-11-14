from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
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

    @staticmethod
    def _average(values: list[float]) -> float | None:
        return round(mean(values), 6) if values else None

    def analytics(self, runtime_mode: str | None = None) -> dict[str, Any]:
        query = "SELECT * FROM run_history"
        parameters: tuple[Any, ...] = ()
        if runtime_mode is not None:
            query += " WHERE runtime_mode = ?"
            parameters = (runtime_mode,)
        query += " ORDER BY created_at ASC"
        with closing(self._connect()) as connection:
            rows = connection.execute(query, parameters).fetchall()

        type_counts: dict[str, int] = {}
        runtime_counts: dict[str, int] = {}
        pipe_metrics: dict[str, dict[str, list[float] | int]] = {}
        optimization_scores: list[float] = []
        leakage_reductions: list[float] = []
        service_gains: list[float] = []
        timeline = []

        for row in rows:
            run_type = str(row["run_type"])
            mode = str(row["runtime_mode"])
            pipe_id = str(row["pipe_id"] or "unknown")
            summary = json.loads(row["summary_json"])
            result = json.loads(row["result_json"])
            type_counts[run_type] = type_counts.get(run_type, 0) + 1
            runtime_counts[mode] = runtime_counts.get(mode, 0) + 1
            bucket = pipe_metrics.setdefault(
                pipe_id,
                {"runs": 0, "scores": [], "affected_nodes": [], "leakage": []},
            )
            bucket["runs"] = int(bucket["runs"]) + 1
            if summary.get("score") is not None:
                score = float(summary["score"])
                optimization_scores.append(score)
                bucket["scores"].append(score)
            if summary.get("maximum_affected_nodes") is not None:
                bucket["affected_nodes"].append(float(summary["maximum_affected_nodes"]))
            if summary.get("total_leakage_volume") is not None:
                bucket["leakage"].append(float(summary["total_leakage_volume"]))

            failure_summary = None
            recovery_summary = None
            if run_type == "manual_recovery":
                failure_summary = result.get("failure", {}).get("summary")
                recovery_summary = result.get("recovery", {}).get("summary")
            elif run_type == "optimization":
                failure_summary = result.get("failure_summary")
                recovery_summary = (result.get("best_candidate") or {}).get("summary")
            if failure_summary and recovery_summary:
                leakage_reductions.append(
                    float(failure_summary.get("total_leakage_volume", 0))
                    - float(recovery_summary.get("total_leakage_volume", 0))
                )
                service_gains.append(
                    float(recovery_summary.get("minimum_service_availability", 0))
                    - float(failure_summary.get("minimum_service_availability", 0))
                )

            timeline.append(
                {
                    "run_id": row["run_id"],
                    "created_at": row["created_at"],
                    "run_type": run_type,
                    "runtime_mode": mode,
                    "pipe_id": row["pipe_id"],
                    "score": summary.get("score"),
                    "service_availability": summary.get("minimum_service_availability"),
                    "affected_nodes": summary.get("maximum_affected_nodes"),
                    "leakage_volume": summary.get("total_leakage_volume"),
                }
            )

        by_pipe = [
            {
                "pipe_id": pipe_id,
                "runs": values["runs"],
                "average_score": self._average(values["scores"]),
                "average_affected_nodes": self._average(values["affected_nodes"]),
                "average_leakage_volume": self._average(values["leakage"]),
            }
            for pipe_id, values in sorted(pipe_metrics.items())
        ]
        return {
            "filter": {"runtime_mode": runtime_mode or "all"},
            "total_runs": len(rows),
            "run_type_counts": type_counts,
            "runtime_counts": runtime_counts,
            "optimization": {
                "run_count": len(optimization_scores),
                "average_score": self._average(optimization_scores),
                "best_score": max(optimization_scores) if optimization_scores else None,
            },
            "recovery": {
                "run_count": len(leakage_reductions),
                "average_leakage_reduction": self._average(leakage_reductions),
                "average_service_gain": self._average(service_gains),
            },
            "by_pipe": by_pipe,
            "timeline": timeline[-30:],
        }
