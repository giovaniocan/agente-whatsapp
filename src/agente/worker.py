"""
Entrypoint do worker de jobs (Plano 11).

Uso: `python -m agente.worker` (ou serviço separado no Coolify).
Consome scheduled_jobs (lembretes, auto-resume, follow-up) em loop.
"""

import asyncio
import logging

from agente.bootstrap import build_runtime
from agente.config.settings import settings


def main() -> None:  # pragma: no cover - loop de produção
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    runtime = build_runtime(settings)
    worker = runtime.build_worker()
    logging.getLogger(__name__).info(
        "worker no ar — tenants: %s", list(runtime.registry_by_id)
    )
    asyncio.run(worker.run_forever())


if __name__ == "__main__":
    main()
