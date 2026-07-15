"""Scheduler Postgres + worker de jobs (Plano 09.1) — contra o banco real."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker

from agente.adapters.scheduler.postgres_scheduler import JobWorker, PostgresScheduler

NOW = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)


async def test_schedule_and_run_due_job(sessionmaker: async_sessionmaker) -> None:
    sched = PostgresScheduler(sessionmaker)
    ran: list[dict] = []

    async def handler(payload: dict) -> None:
        ran.append(payload)

    await sched.schedule("reminder", NOW - timedelta(minutes=1), {"phone": "44"}, None)
    await sched.schedule("reminder", NOW + timedelta(hours=1), {"phone": "55"}, None)

    worker = JobWorker(sessionmaker, {"reminder": handler})
    processed = await worker.run_once(now=NOW)

    assert processed == 1
    assert ran == [{"phone": "44"}]          # só o vencido rodou; o futuro ficou


async def test_failed_job_retries_then_fails(sessionmaker: async_sessionmaker) -> None:
    sched = PostgresScheduler(sessionmaker)

    async def broken(payload: dict) -> None:
        raise RuntimeError("boom")

    await sched.schedule("reminder", NOW - timedelta(minutes=1), {}, None)
    worker = JobWorker(sessionmaker, {"reminder": broken}, max_attempts=3, retry_delay_s=0)

    for _ in range(3):
        await worker.run_once(now=NOW + timedelta(hours=1))

    statuses = await _statuses(sessionmaker)
    assert statuses == ["failed"]            # nunca some silenciosamente (visível)


async def test_cancel_by_correlation_skips_execution(
    sessionmaker: async_sessionmaker,
) -> None:
    sched = PostgresScheduler(sessionmaker)
    ran: list[dict] = []

    async def handler(payload: dict) -> None:
        ran.append(payload)

    await sched.schedule("reminder", NOW - timedelta(minutes=1), {}, correlation_id="appt-1")
    await sched.cancel_by_correlation("appt-1")

    worker = JobWorker(sessionmaker, {"reminder": handler})
    processed = await worker.run_once(now=NOW)

    assert processed == 0 and ran == []
    assert await _statuses(sessionmaker) == ["cancelled"]


async def test_unknown_kind_is_marked_failed(sessionmaker: async_sessionmaker) -> None:
    sched = PostgresScheduler(sessionmaker)
    await sched.schedule("mistery", NOW - timedelta(minutes=1), {}, None)

    worker = JobWorker(sessionmaker, {}, max_attempts=1)
    await worker.run_once(now=NOW)

    assert await _statuses(sessionmaker) == ["failed"]


async def _statuses(sessionmaker: async_sessionmaker) -> list[str]:
    from sqlalchemy import select

    from agente.adapters.store.models import ScheduledJobRow

    async with sessionmaker() as session:
        rows = await session.scalars(select(ScheduledJobRow.status))
        return sorted(rows.all())
