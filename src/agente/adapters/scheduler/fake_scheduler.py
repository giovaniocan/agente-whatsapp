"""
FakeScheduler — SchedulerPort em memória (suporte de teste e demo).

Guarda os jobs para inspeção. O worker real (Postgres) vem no plano 09.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel


class ScheduledJob(BaseModel):
    id: str
    kind: str
    run_at: datetime
    payload: dict[str, Any]


class FakeScheduler:
    def __init__(self) -> None:
        self.jobs: dict[str, ScheduledJob] = {}

    async def schedule(self, kind: str, run_at: datetime, payload: dict[str, Any]) -> str:
        job = ScheduledJob(id=uuid4().hex, kind=kind, run_at=run_at, payload=payload)
        self.jobs[job.id] = job
        return job.id

    async def cancel(self, job_id: str) -> None:
        self.jobs.pop(job_id, None)
