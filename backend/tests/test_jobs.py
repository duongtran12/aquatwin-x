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


def test_job_manager_cancels_queued_job() -> None:
    manager = JobManager(max_workers=1)
    release = Event()
    first = manager.submit(lambda: (release.wait(timeout=2), {"done": True})[1])
    queued = manager.submit_progress(
        lambda job_id, report: {"job_id": job_id},
        total_steps=1,
    )

    cancelled = manager.cancel(queued["job_id"])
    release.set()

    assert cancelled["status"] == "cancelled"
    assert manager.status(queued["job_id"])["status"] == "cancelled"
    with pytest.raises(RuntimeError, match="cancelled"):
        manager.result(queued["job_id"])
    for _ in range(100):
        if manager.status(first["job_id"])["status"] == "completed":
            break
        sleep(0.001)
    manager.shutdown()


def test_job_manager_cooperatively_cancels_running_progress_job() -> None:
    manager = JobManager(max_workers=1)
    started = Event()
    continue_work = Event()

    def task(job_id, report):
        started.set()
        continue_work.wait(timeout=2)
        report(1, 2, "First run")
        return {"job_id": job_id}

    job = manager.submit_progress(task, total_steps=2)
    assert started.wait(timeout=2)
    cancelling = manager.cancel(job["job_id"])
    continue_work.set()

    assert cancelling["status"] == "cancelling"
    for _ in range(100):
        current = manager.status(job["job_id"])
        if current["status"] == "cancelled":
            break
        sleep(0.001)
    assert current["status"] == "cancelled"
    assert current["progress"]["message"] == "Cancelled by user"
    manager.shutdown()


def test_job_manager_rejects_cancelling_running_atomic_job() -> None:
    manager = JobManager(max_workers=1)
    started = Event()
    release = Event()

    def task():
        started.set()
        release.wait(timeout=2)
        return {"done": True}

    job = manager.submit(task)
    assert started.wait(timeout=2)
    with pytest.raises(RuntimeError, match="cannot be cancelled safely"):
        manager.cancel(job["job_id"])
    release.set()
    manager.shutdown()

