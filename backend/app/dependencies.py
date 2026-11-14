from backend.app.config import get_settings
from backend.app.services.aquatwin_service import AquaTwinService
from backend.app.services.history import RunHistoryStore
from backend.app.services.jobs import JobManager


_history = RunHistoryStore()
_service = AquaTwinService(get_settings().aquatwin_runtime_mode, _history)
_jobs = JobManager(max_workers=1)


def get_aquatwin_service() -> AquaTwinService:
    return _service


def get_job_manager() -> JobManager:
    return _jobs


def get_history_store() -> RunHistoryStore:
    return _history

