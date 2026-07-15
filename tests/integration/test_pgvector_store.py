"""RAG em pgvector (Plano 10) — ingestão idempotente, busca e ISOLAMENTO."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from agente.adapters.store.models import KnowledgeChunkRow
from agente.adapters.vectorstore.embedder import FakeEmbedder
from agente.adapters.vectorstore.pgvector_store import PgVectorKnowledgeStore

FAQ_SALAO = (
    "Unha em gel: aplicamos em até 60 minutos, com garantia de 15 dias.\n\n"
    "Corte feminino: atendemos de segunda a sábado, sem hora marcada aos sábados."
)


def _store(sessionmaker: async_sessionmaker) -> PgVectorKnowledgeStore:
    return PgVectorKnowledgeStore(sessionmaker, FakeEmbedder(dim=32))


async def test_ingest_is_idempotent(sessionmaker: async_sessionmaker) -> None:
    store = _store(sessionmaker)

    first = await store.ingest("salao", FAQ_SALAO, source="faq.md")
    second = await store.ingest("salao", FAQ_SALAO, source="faq.md")   # re-ingestão

    assert first >= 1 and second == 0            # nada duplica (hash do conteúdo)
    async with sessionmaker() as session:
        count = await session.scalar(select(func.count(KnowledgeChunkRow.id)))
    assert count == first


async def test_search_returns_most_relevant_chunk(
    sessionmaker: async_sessionmaker,
) -> None:
    store = _store(sessionmaker)
    await store.ingest("salao", FAQ_SALAO, source="faq.md")
    await store.ingest("salao", "Estacionamento gratuito para clientes.", source="faq.md")

    results = await store.search("salao", "quanto tempo demora unha em gel?", k=1)

    assert len(results) == 1
    assert "gel" in results[0]                    # o chunk certo veio primeiro


async def test_tenant_isolation_is_hard(sessionmaker: async_sessionmaker) -> None:
    # RN-01/plano 10: chunk do salão JAMAIS aparece para a revenda.
    store = _store(sessionmaker)
    await store.ingest("salao", FAQ_SALAO, source="faq.md")

    assert await store.search("revenda", "unha em gel", k=5) == []
