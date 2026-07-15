"""
PgVectorKnowledgeStore — base de conhecimento por tenant (KnowledgePort).

Ingestão: chunking com overlap → hash sha256 por chunk → embedding → upsert
idempotente (ON CONFLICT DO NOTHING no par tenant+hash). Re-ingerir o mesmo
arquivo não duplica nada.

Busca: cosine distance do pgvector, SEMPRE filtrada por tenant_id — o
isolamento é duro, testado explicitamente (chunk de um tenant nunca vaza).
"""

import hashlib

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agente.adapters.store.models import KnowledgeChunkRow
from agente.domain.ports import EmbeddingPort
from agente.utils.chunking import chunk_text


class PgVectorKnowledgeStore:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        embedder: EmbeddingPort,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._embedder = embedder

    async def ingest(self, tenant_id: str, text: str, source: str = "") -> int:
        """Ingere um documento; devolve quantos chunks NOVOS entraram."""
        chunks = chunk_text(text)
        if not chunks:
            return 0
        vectors = await self._embedder.embed(chunks)

        inserted = 0
        async with self._sessionmaker() as session:
            for content, vector in zip(chunks, vectors, strict=True):
                stmt = (
                    pg_insert(KnowledgeChunkRow)
                    .values(
                        tenant_id=tenant_id,
                        source=source,
                        content=content,
                        content_hash=hashlib.sha256(content.encode()).hexdigest(),
                        embedding=vector,
                    )
                    .on_conflict_do_nothing(constraint="uq_chunk_tenant_hash")
                    .returning(KnowledgeChunkRow.id)
                )
                if await session.scalar(stmt) is not None:
                    inserted += 1
            await session.commit()
        return inserted

    async def search(self, tenant_id: str, query: str, k: int = 5) -> list[str]:
        [vector] = await self._embedder.embed([query])
        async with self._sessionmaker() as session:
            rows = await session.scalars(
                select(KnowledgeChunkRow.content)
                .where(KnowledgeChunkRow.tenant_id == tenant_id)   # isolamento duro
                .order_by(KnowledgeChunkRow.embedding.cosine_distance(vector))
                .limit(k)
            )
            return list(rows.all())
