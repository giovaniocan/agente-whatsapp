"""
Entrypoint HTTP de produção: `uvicorn agente.api.main:app`.

Toda a fiação vem do bootstrap (fichas + fábricas + pipeline + webhook).
Conexões de banco só acontecem por requisição — importar este módulo não
exige Postgres no ar.
"""

import logging

from agente.bootstrap import build_runtime
from agente.config.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

runtime = build_runtime(settings)
app = runtime.app
