from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from threading import Lock
from typing import Any, Callable
from uuid import uuid4


class JobManager:
    def __init__(self, max_workers: int = 1) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="aquatwin-optimization",
        )
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).isoformat()

    def submit(self, task: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        job_id = uuid4().hex
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "created_at": self._timestamp(),
                "started_at": None,
                "completed_at": None,
                "result": None,
                "error": None,
            }
        self._executor.submit(self._execute, job_id, task)
        return self.status(job_id)

    def _execute(self, job_id: str, task: Callable[[], dict[str, Any]]) -> None:
        with self._lock:
            self._jobs[job_id]["status"] = "running"
            self._jobs[job_id]["started_at"] = self._timestamp()
        try:
            result = task()
        except Exception as exc:
            with self._lock:
                self._jobs[job_id]["status"] = "failed"
                self._jobs[job_id]["error"] = str(exc)
                self._jobs[job_id]["completed_at"] = self._timestamp()
        else:
            with self._lock:
                self._jobs[job_id]["status"] = "completed"
                self._jobs[job_id]["result"] = result
                self._jobs[job_id]["completed_at"] = self._timestamp()

    def _get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return deepcopy(self._jobs[job_id])

    def status(self, job_id: str) -> dict[str, Any]:
        job = self._get(job_id)
        job.pop("result")
        return job

    def result(self, job_id: str) -> dict[str, Any]:
        job = self._get(job_id)
        if job["status"] != "completed":
            raise RuntimeError(job["status"])
        return job["result"]

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

