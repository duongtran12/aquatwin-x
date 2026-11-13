from backend.app.services.aquatwin_service import AquaTwinService
from backend.app.services.jobs import JobManager


_service = AquaTwinService()
_jobs = JobManager(max_workers=1)


def get_aquatwin_service() -> AquaTwinService:
    return _service


def get_job_manager() -> JobManager:
    return _jobs

