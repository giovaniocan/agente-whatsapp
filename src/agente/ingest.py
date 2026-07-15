"""
CLI de ingestão da base de conhecimento (Plano 10.2).

Uso:
    DATABASE_URL=postgresql+asyncpg://... uv run python -m agente.ingest <tenant_id> <arquivo>

Embeddings: usa OpenAI se OPENAI_API_KEY estiver no ambiente; senão cai no
FakeEmbedder (bag-of-words — suficiente para demo/dev, NÃO para produção).
Decisão do provedor definitivo (OpenAI vs Voyage) está em docs/PENDENCIAS.md.
"""

import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agente.adapters.vectorstore.embedder import FakeEmbedder, OpenAIEmbedder
from agente.adapters.vectorstore.pgvector_store import PgVectorKnowledgeStore
from agente.domain.ports import EmbeddingPort


def _embedder() -> EmbeddingPort:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        return OpenAIEmbedder(api_key=api_key)
    print("aviso: OPENAI_API_KEY ausente — usando FakeEmbedder (só dev/demo)")
    return FakeEmbedder()


async def _run(tenant_id: str, path: Path) -> None:
    database_url = os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://agente:agente@localhost:5439/agente"
    )
    engine = create_async_engine(database_url)
    store = PgVectorKnowledgeStore(async_sessionmaker(engine), _embedder())
    inserted = await store.ingest(tenant_id, path.read_text(), source=path.name)
    await engine.dispose()
    print(f"{inserted} chunk(s) novos ingeridos de {path.name} para {tenant_id!r}")


def main() -> None:
    if len(sys.argv) != 3:
        print("uso: python -m agente.ingest <tenant_id> <arquivo>")
        raise SystemExit(2)
    asyncio.run(_run(sys.argv[1], Path(sys.argv[2])))


if __name__ == "__main__":
    main()
