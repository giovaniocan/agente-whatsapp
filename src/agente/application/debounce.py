"""
DebounceBuffer — agrupa mensagens em rajada antes de chamar o cérebro (RN-43).

Pessoas mandam 3-4 mensagens seguidas; enviar cada uma ao LLM é caro e a
resposta fica picada. Aqui abrimos uma janela por conversa: as mensagens que
chegam nela são concatenadas e processadas UMA vez, dentro do lock (RN-44).

É o "processador" injetado no webhook. O relógio (`sleep`) é injetável para os
testes rodarem determinísticos.
"""

import asyncio
from collections.abc import Awaitable, Callable

from agente.domain.messaging import IncomingMessage
from agente.domain.ports import ConversationStorePort
from agente.domain.tenant import Tenant

Downstream = Callable[[Tenant, str], Awaitable[None]]
Sleep = Callable[[float], Awaitable[None]]

_Key = tuple[str, str]


class DebounceBuffer:
    def __init__(
        self,
        downstream: Downstream,
        store: ConversationStorePort,
        window: float = 6.0,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._downstream = downstream
        self._store = store
        self._window = window
        self._sleep = sleep
        self._buffers: dict[_Key, list[str]] = {}
        self._tenants: dict[_Key, Tenant] = {}
        self._tasks: dict[_Key, asyncio.Task[None]] = {}

    async def __call__(self, tenant: Tenant, incoming: IncomingMessage) -> None:
        phone = incoming.phone or incoming.lid or ""
        key = (tenant.id, phone)
        self._tenants[key] = tenant
        self._buffers.setdefault(key, []).append(incoming.text)
        # abre a janela só se não houver uma aberta para esta conversa.
        if key not in self._tasks or self._tasks[key].done():
            self._tasks[key] = asyncio.create_task(self._flush_after(key, phone))

    async def _flush_after(self, key: _Key, phone: str) -> None:
        await self._sleep(self._window)
        texts = self._buffers.pop(key, [])
        tenant = self._tenants.pop(key, None)
        self._tasks.pop(key, None)
        if not texts or tenant is None:
            return
        grouped = "\n".join(texts)
        async with self._store.lock(f"{tenant.id}:{phone}"):
            await self._downstream(tenant, grouped)

    async def drain(self) -> None:
        """Espera todas as janelas abertas fecharem (usado em testes/shutdown)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks.values()))
