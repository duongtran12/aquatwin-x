from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable
from uuid import uuid4


class JobCancelled(Exception):
    pass


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
        return datetime.now(timezone.utc).isoformat()

    def _create_job(
        self,
        total_steps: int | None = None,
        cancellable: bool = False,
    ) -> str:
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
                "cancellable": cancellable,
                "cancel_requested": False,
                "progress": {
                    "completed_steps": 0,
                    "total_steps": total_steps,
                    "percent": 0.0,
                    "message": "Waiting to start",
                },
            }
        return job_id

    def submit(self, task: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        job_id = self._create_job()
        self._executor.submit(self._execute, job_id, task)
        return self.status(job_id)

    def submit_progress(
        self,
        task: Callable[[str, Callable[[int, int, str], None]], dict[str, Any]],
        total_steps: int,
    ) -> dict[str, Any]:
        job_id = self._create_job(total_steps, cancellable=True)
        self._executor.submit(self._execute_progress, job_id, task)
        return self.status(job_id)

    def _report_progress(self, job_id: str, completed: int, total: int, message: str) -> None:
        with self._lock:
            if self._jobs[job_id]["cancel_requested"]:
                raise JobCancelled
            progress = self._jobs[job_id]["progress"]
            progress.update({
                "completed_steps": completed,
                "total_steps": total,
                "percent": round(completed / total * 100, 2) if total else 0.0,
                "message": message,
            })

    def _execute_progress(
        self,
        job_id: str,
        task: Callable[[str, Callable[[int, int, str], None]], dict[str, Any]],
    ) -> None:
        self._execute(
            job_id,
            lambda: task(
                job_id,
                lambda completed, total, message: self._report_progress(
                    job_id, completed, total, message
                ),
            ),
        )

    def _execute(self, job_id: str, task: Callable[[], dict[str, Any]]) -> None:
        with self._lock:
            if self._jobs[job_id]["cancel_requested"]:
                return
            self._jobs[job_id]["status"] = "running"
            self._jobs[job_id]["started_at"] = self._timestamp()
        try:
            result = task()
        except JobCancelled:
            with self._lock:
                self._mark_cancelled(job_id)
        except Exception as exc:
            with self._lock:
                self._jobs[job_id]["status"] = "failed"
                self._jobs[job_id]["error"] = str(exc)
                self._jobs[job_id]["completed_at"] = self._timestamp()
        else:
            with self._lock:
                if self._jobs[job_id]["cancel_requested"]:
                    self._mark_cancelled(job_id)
                    return
                self._jobs[job_id]["status"] = "completed"
                self._jobs[job_id]["result"] = result
                self._jobs[job_id]["completed_at"] = self._timestamp()
                progress = self._jobs[job_id]["progress"]
                if progress["total_steps"] is not None:
                    progress["completed_steps"] = progress["total_steps"]
                    progress["percent"] = 100.0
                    progress["message"] = "Completed"

    def _mark_cancelled(self, job_id: str) -> None:
        job = self._jobs[job_id]
        job["status"] = "cancelled"
        job["completed_at"] = self._timestamp()
        job["progress"]["message"] = "Cancelled by user"

    def cancel(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            job = self._jobs[job_id]
            if job["status"] in {"completed", "failed", "cancelled"}:
                return self._public_status(job)
            if job["status"] == "running" and not job["cancellable"]:
                raise RuntimeError("This running job cannot be cancelled safely")
            job["cancel_requested"] = True
            if job["status"] == "queued":
                self._mark_cancelled(job_id)
            else:
                job["status"] = "cancelling"
                job["progress"]["message"] = "Cancellation requested"
            return self._public_status(job)

    @staticmethod
    def _public_status(job: dict[str, Any]) -> dict[str, Any]:
        public = deepcopy(job)
        public.pop("result")
        public.pop("cancel_requested")
        return public

    def _get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return deepcopy(self._jobs[job_id])

    def status(self, job_id: str) -> dict[str, Any]:
        job = self._get(job_id)
        return self._public_status(job)

    def result(self, job_id: str) -> dict[str, Any]:
        job = self._get(job_id)
        if job["status"] != "completed":
            raise RuntimeError(job["status"])
        return job["result"]

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

