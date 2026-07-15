"""
Fixtures de integração — Postgres real (container docker-compose, porta 5439).

Cada teste roda com o schema recriado do zero (create_all/drop_all), isolado.
Se o banco não estiver de pé, os testes são pulados (não quebram a suíte).
"""

import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agente.adapters.store.models import Base

TEST_DB_URL = os.environ.get(
    "AGENTE_TEST_DATABASE_URL",
    "postgresql+asyncpg://agente:agente@localhost:5439/agente",
)


@pytest_asyncio.fixture
async def sessionmaker() -> object:
    engine = create_async_engine(TEST_DB_URL)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Postgres de teste indisponível ({exc})")
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()
