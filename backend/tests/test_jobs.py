from threading import Event
from time import sleep

import pytest

from backend.app.services.jobs import JobManager


def test_job_manager_returns_completed_result() -> None:
    manager = JobManager(max_workers=1)
    completed = Event()

    def task() -> dict[str, int]:
        completed.set()
        return {"score": 95}

    job = manager.submit(task)
    assert completed.wait(timeout=2)

    for _ in range(100):
        if manager.status(job["job_id"])["status"] == "completed":
            break
        sleep(0.001)

    assert manager.status(job["job_id"])["status"] == "completed"
    assert manager.result(job["job_id"]) == {"score": 95}
    manager.shutdown()


def test_job_manager_records_failure() -> None:
    manager = JobManager(max_workers=1)
    completed = Event()

    def task() -> dict[str, int]:
        completed.set()
        raise ValueError("invalid candidate")

    job = manager.submit(task)
    assert completed.wait(timeout=2)

    for _ in range(100):
        if manager.status(job["job_id"])["status"] == "failed":
            break
        sleep(0.001)

    status = manager.status(job["job_id"])
    assert status["status"] == "failed"
    assert status["error"] == "invalid candidate"
    with pytest.raises(RuntimeError):
        manager.result(job["job_id"])
    manager.shutdown()


def test_job_manager_reports_progress() -> None:
    manager = JobManager(max_workers=1)
    completed = Event()

    def task(job_id, report):
        report(2, 4, "Halfway")
        completed.set()
        return {"job_id": job_id}

    job = manager.submit_progress(task, total_steps=4)
    assert completed.wait(timeout=2)
    for _ in range(100):
        current = manager.status(job["job_id"])
        if current["status"] == "completed":
            break
        sleep(0.001)
    assert current["progress"]["percent"] == 100.0
    assert manager.result(job["job_id"])["job_id"] == job["job_id"]
    manager.shutdown()

