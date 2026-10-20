"""In-memory data store for IncuBrix projects, jobs, and idempotency cache."""
from typing import Optional, Dict, Any
from app.core.models import Project


class DataStore:
    _instance: Optional["DataStore"] = None

    def __new__(cls) -> "DataStore":
        if cls._instance is None:
            cls._instance = super(DataStore, cls).__new__(cls)
            cls._instance.projects = {}
            cls._instance.jobs = {}
            cls._instance.idempotency_keys = {}
        return cls._instance

    def __init__(self) -> None:
        # Initialized in __new__
        pass

    def save_project(self, project: Project) -> None:
        self.projects[str(project.id)] = project

    def get_project(self, project_id: str) -> Optional[Project]:
        if not project_id:
            return None
        pid = str(project_id)
        if pid in self.projects:
            return self.projects[pid]
        # Also allow lookup by source_media.id
        for p in self.projects.values():
            if str(p.source_media.id) == pid:
                return p
        return None

    def list_projects(self) -> list[Project]:
        return list(self.projects.values())

    def delete_project(self, project_id: str) -> bool:
        if str(project_id) in self.projects:
            del self.projects[str(project_id)]
            return True
        return False

    def save_job(self, job_id: str, job: Dict[str, Any]) -> None:
        self.jobs[str(job_id)] = job

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.jobs.get(str(job_id))

    def list_jobs(self) -> list[Dict[str, Any]]:
        return list(self.jobs.values())

    def save_idempotency(self, key: str, data: Dict[str, Any]) -> None:
        self.idempotency_keys[key] = data

    def get_idempotency(self, key: str) -> Optional[Dict[str, Any]]:
        return self.idempotency_keys.get(key)

    def clear(self) -> None:
        self.projects.clear()
        self.jobs.clear()
        self.idempotency_keys.clear()


_db_singleton = DataStore()


def get_db() -> DataStore:
    return _db_singleton
