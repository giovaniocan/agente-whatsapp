"""DebounceBuffer — agrupa rajada (RN-43) e processa dentro do lock (RN-44)."""

import asyncio
from collections.abc import Callable

from agente.adapters.store.fake_store import FakeConversationStore
from agente.application.debounce import DebounceBuffer
from agente.domain.messaging import IncomingMessage
from agente.domain.tenant import Tenant


def _msg(text: str, mid: str) -> IncomingMessage:
    return IncomingMessage(text=text, message_id=mid, phone="44999998888")


async def test_burst_is_grouped_into_a_single_call(
    make_tenant: Callable[..., Tenant],
) -> None:
    processed: list[str] = []

    async def downstream(tenant: Tenant, text: str) -> None:
        processed.append(text)

    release = asyncio.Event()

    async def fake_sleep(_: float) -> None:
        await release.wait()   # a "janela" só fecha quando o teste liberar

    buf = DebounceBuffer(downstream, FakeConversationStore(), window=6, sleep=fake_sleep)
    tenant = make_tenant()

    await buf(tenant, _msg("oi", "m1"))
    await buf(tenant, _msg("quero", "m2"))
    await buf(tenant, _msg("agendar", "m3"))

    assert processed == []          # janela ainda aberta, nada processado
    release.set()
    await buf.drain()               # espera o flush

    assert processed == ["oi\nquero\nagendar"]   # uma chamada só, agrupada


async def test_processing_runs_inside_the_conversation_lock(
    make_tenant: Callable[..., Tenant],
) -> None:
    locked_keys: list[str] = []
    store = FakeConversationStore()
    original_lock = store.lock

    def spy_lock(key: str):  # type: ignore[no-untyped-def]
        locked_keys.append(key)
        return original_lock(key)

    store.lock = spy_lock  # type: ignore[method-assign]

    async def downstream(tenant: Tenant, text: str) -> None: ...

    buf = DebounceBuffer(downstream, store, window=0, sleep=_no_wait)
    await buf(make_tenant(), _msg("oi", "m1"))
    await buf.drain()

    assert locked_keys == ["salao:44999998888"]


async def _no_wait(_: float) -> None:
    return None
