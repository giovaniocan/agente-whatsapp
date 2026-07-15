"""
PostgresConversationStore — implementa a ConversationStorePort.

Carrega/salva a Conversation (traduzindo entre a entidade de domínio e a linha
ORM) e faz o dedupe idempotente de mensagens (RN-42).
"""

import hashlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agente.adapters.store.models import ConversationRow, ProcessedMessageRow
from agente.domain.conversation import Conversation
from agente.domain.enums import HandoffStatus
from agente.domain.lead import LeadInfo


class PostgresConversationStore:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def get_or_create(self, tenant_id: str, phone: str) -> Conversation:
        async with self._sessionmaker() as session:
            row = await session.scalar(
                select(ConversationRow).where(
                    ConversationRow.tenant_id == tenant_id,
                    ConversationRow.phone == phone,
                )
            )
            if row is None:
                row = ConversationRow(tenant_id=tenant_id, phone=phone)
                session.add(row)
                await session.commit()
                await session.refresh(row)
            return self._to_domain(row)

    async def save(self, conversation: Conversation) -> None:
        async with self._sessionmaker() as session:
            row = await session.scalar(
                select(ConversationRow).where(
                    ConversationRow.tenant_id == conversation.tenant_id,
                    ConversationRow.phone == conversation.phone,
                )
            )
            if row is None:
                row = ConversationRow(
                    tenant_id=conversation.tenant_id, phone=conversation.phone
                )
                session.add(row)
            row.handoff_status = conversation.handoff_status.value
            row.lead_draft = (
                conversation.lead_draft.model_dump()
                if conversation.lead_draft is not None
                else None
            )
            row.summary = conversation.summary
            row.updated_at = conversation.updated_at
            await session.commit()

    async def mark_message_seen(self, provider_message_id: str) -> bool:
        # INSERT ... ON CONFLICT DO NOTHING: se nada foi inserido, já existia.
        async with self._sessionmaker() as session:
            stmt = (
                pg_insert(ProcessedMessageRow)
                .values(provider_message_id=provider_message_id)
                .on_conflict_do_nothing(index_elements=["provider_message_id"])
                .returning(ProcessedMessageRow.provider_message_id)
            )
            inserted = await session.scalar(stmt)
            await session.commit()
            return inserted is None   # None = conflito = já vista

    @asynccontextmanager
    async def lock(self, key: str) -> AsyncIterator[None]:
        # advisory lock por conexão: pg_advisory_lock bloqueia até liberar (RN-44).
        lock_key = self._key_to_bigint(key)
        async with self._sessionmaker() as session:
            await session.execute(text("SELECT pg_advisory_lock(:k)"), {"k": lock_key})
            try:
                yield
            finally:
                await session.execute(
                    text("SELECT pg_advisory_unlock(:k)"), {"k": lock_key}
                )
                await session.commit()

    @staticmethod
    def _key_to_bigint(key: str) -> int:
        # bigint assinado de 64 bits estável para a chave da conversa.
        digest = hashlib.sha256(key.encode()).digest()[:8]
        return int.from_bytes(digest, "big", signed=True)

    def _to_domain(self, row: ConversationRow) -> Conversation:
        draft = LeadInfo.model_validate(row.lead_draft) if row.lead_draft else None
        return Conversation(
            tenant_id=row.tenant_id,
            phone=row.phone,
            handoff_status=HandoffStatus(row.handoff_status),
            lead_draft=draft,
            summary=row.summary,
            updated_at=row.updated_at,
        )
