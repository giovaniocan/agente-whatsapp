"""
Scheduler Postgres (Plano 09) — SchedulerPort real + worker de jobs.

- PostgresScheduler: grava/cancela jobs na tabela `scheduled_jobs`.
- JobWorker: consome jobs vencidos com FOR UPDATE SKIP LOCKED (várias réplicas
  não duplicam execução), com retry/backoff e falha VISÍVEL (status `failed`,
  nunca some silenciosamente).

Handlers são injetados: {kind -> async fn(payload)}. Kind sem handler = failed.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agente.adapters.store.models import ScheduledJobRow

logger = logging.getLogger(__name__)

JobHandler = Callable[[dict[str, Any]], Awaitable[None]]

_RUNNABLE = ("pending", "retrying")


class PostgresScheduler:
    """Implementa a SchedulerPort sobre a tabela scheduled_jobs."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def schedule(
        self,
        kind: str,
        run_at: datetime,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> str:
        async with self._sessionmaker() as session:
            row = ScheduledJobRow(
                kind=kind, run_at=run_at, payload=payload, correlation_id=correlation_id
            )
            session.add(row)
            await session.commit()
            return str(row.id)

    async def cancel(self, job_id: str) -> None:
        async with self._sessionmaker() as session:
            row = await session.get(ScheduledJobRow, int(job_id))
            if row is not None and row.status in _RUNNABLE:
                row.status = "cancelled"
            await session.commit()

    async def cancel_by_correlation(self, correlation_id: str) -> None:
        async with self._sessionmaker() as session:
            rows = await session.scalars(
                select(ScheduledJobRow).where(
                    ScheduledJobRow.correlation_id == correlation_id,
                    ScheduledJobRow.status.in_(_RUNNABLE),
                )
            )
            for row in rows:
                row.status = "cancelled"
            await session.commit()


class JobWorker:
    """Executa jobs vencidos. `run_once` processa um lote; `run_forever` faz o loop."""

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        handlers: Mapping[str, JobHandler],
        max_attempts: int = 3,
        retry_delay_s: int = 60,
        batch_size: int = 20,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._handlers = handlers
        self._max_attempts = max_attempts
        self._retry_delay_s = retry_delay_s
        self._batch_size = batch_size

    async def run_once(self, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        claimed = await self._claim_due(now)
        for job_id, kind, payload in claimed:
            await self._execute(job_id, kind, payload, now)
        return len(claimed)

    async def run_forever(self, poll_interval_s: float = 5.0) -> None:  # pragma: no cover
        while True:
            try:
                processed = await self.run_once()
            except Exception:
                logger.exception("job worker: erro no ciclo")
                processed = 0
            if processed == 0:
                await asyncio.sleep(poll_interval_s)

    async def _claim_due(self, now: datetime) -> list[tuple[int, str, dict[str, Any]]]:
        # SKIP LOCKED: réplicas concorrentes não pegam o mesmo job.
        async with self._sessionmaker() as session:
            rows = await session.scalars(
                select(ScheduledJobRow)
                .where(
                    ScheduledJobRow.status.in_(_RUNNABLE),
                    ScheduledJobRow.run_at <= now,
                )
                .order_by(ScheduledJobRow.run_at)
                .limit(self._batch_size)
                .with_for_update(skip_locked=True)
            )
            claimed: list[tuple[int, str, dict[str, Any]]] = []
            for row in rows:
                row.status = "running"
                row.attempts += 1
                claimed.append((row.id, row.kind, dict(row.payload)))
            await session.commit()
            return claimed

    async def _execute(
        self, job_id: int, kind: str, payload: dict[str, Any], now: datetime
    ) -> None:
        handler = self._handlers.get(kind)
        try:
            if handler is None:
                raise LookupError(f"sem handler para kind={kind!r}")
            await handler(payload)
        except Exception:
            logger.exception("job %s (%s) falhou", job_id, kind)
            await self._mark_failure(job_id, now)
            return
        await self._set_status(job_id, "done")

    async def _mark_failure(self, job_id: int, now: datetime) -> None:
        async with self._sessionmaker() as session:
            row = await session.get(ScheduledJobRow, job_id)
            if row is None:  # pragma: no cover - corrida improvável
                return
            if row.attempts >= self._max_attempts:
                row.status = "failed"           # visível para operação/alerta
            else:
                row.status = "retrying"         # backoff simples e explícito
                row.run_at = now + timedelta(seconds=self._retry_delay_s * row.attempts)
            await session.commit()

    async def _set_status(self, job_id: int, status: str) -> None:
        async with self._sessionmaker() as session:
            row = await session.get(ScheduledJobRow, job_id)
            if row is not None:
                row.status = status
            await session.commit()
