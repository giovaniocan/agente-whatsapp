"""
FakeConversationStore — ConversationStorePort em memória.

Para testes de API/aplicação sem Postgres. Espelha o comportamento do
PostgresConversationStore (dedupe idempotente, histórico, lock por chave).
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from agente.domain.conversation import Conversation
from agente.domain.messaging import StoredMessage


class FakeConversationStore:
    def __init__(self) -> None:
        self._conversations: dict[tuple[str, str], Conversation] = {}
        self._seen: set[str] = set()
        self._messages: dict[tuple[str, str], list[StoredMessage]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def get_or_create(self, tenant_id: str, phone: str) -> Conversation:
        key = (tenant_id, phone)
        if key not in self._conversations:
            self._conversations[key] = Conversation(tenant_id=tenant_id, phone=phone)
        return self._conversations[key]

    async def save(self, conversation: Conversation) -> None:
        self._conversations[(conversation.tenant_id, conversation.phone)] = conversation

    async def mark_message_seen(self, provider_message_id: str) -> bool:
        if provider_message_id in self._seen:
            return True
        self._seen.add(provider_message_id)
        return False

    async def add_message(
        self,
        tenant_id: str,
        phone: str,
        direction: str,
        text: str,
        provider_message_id: str | None = None,
    ) -> None:
        self._messages.setdefault((tenant_id, phone), []).append(
            StoredMessage(direction=direction, text=text)
        )

    async def recent_messages(
        self, tenant_id: str, phone: str, limit: int
    ) -> list[StoredMessage]:
        return self._messages.get((tenant_id, phone), [])[-limit:]

    @asynccontextmanager
    async def lock(self, key: str) -> AsyncIterator[None]:
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            yield
