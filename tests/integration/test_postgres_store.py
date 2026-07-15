"""Repositório de conversa em Postgres — RN-42 (dedupe) e persistência."""

from sqlalchemy.ext.asyncio import async_sessionmaker

from agente.adapters.store.postgres_store import PostgresConversationStore
from agente.domain.enums import HandoffStatus
from agente.domain.lead import LeadInfo


async def test_get_or_create_is_idempotent(sessionmaker: async_sessionmaker) -> None:
    store = PostgresConversationStore(sessionmaker)

    first = await store.get_or_create("salao", "44999998888")
    again = await store.get_or_create("salao", "44999998888")

    assert first.tenant_id == "salao"
    assert again.phone == "44999998888"
    assert again.handoff_status is HandoffStatus.ACTIVE


async def test_save_persists_handoff_and_lead_draft(
    sessionmaker: async_sessionmaker,
) -> None:
    store = PostgresConversationStore(sessionmaker)
    conv = await store.get_or_create("salao", "44999998888")

    conv.request_handoff()
    conv.lead_draft = LeadInfo(full_name="Maria", phone="44999998888", intent="nails")
    conv.summary = "quer unha em gel"
    await store.save(conv)

    reloaded = await store.get_or_create("salao", "44999998888")
    assert reloaded.handoff_status is HandoffStatus.PENDING
    assert reloaded.lead_draft is not None
    assert reloaded.lead_draft.full_name == "Maria"
    assert reloaded.summary == "quer unha em gel"


async def test_mark_message_seen_dedupes(sessionmaker: async_sessionmaker) -> None:
    # RN-42: o webhook pode reentregar; a 2ª vez é ignorada.
    store = PostgresConversationStore(sessionmaker)

    assert await store.mark_message_seen("MSG-1") is False   # nova
    assert await store.mark_message_seen("MSG-1") is True    # repetida
    assert await store.mark_message_seen("MSG-2") is False   # outra, nova


async def test_lock_serializes_same_conversation(sessionmaker: async_sessionmaker) -> None:
    # RN-44: duas mensagens da mesma conversa nunca processam em paralelo.
    import asyncio

    store = PostgresConversationStore(sessionmaker)
    order: list[str] = []

    async def worker(name: str, hold: float) -> None:
        async with store.lock("conv:salao:44999998888"):
            order.append(f"{name}-enter")
            await asyncio.sleep(hold)
            order.append(f"{name}-exit")

    a = asyncio.create_task(worker("A", 0.2))
    await asyncio.sleep(0.05)          # garante que A pega o lock primeiro
    b = asyncio.create_task(worker("B", 0.0))
    await asyncio.gather(a, b)

    assert order == ["A-enter", "A-exit", "B-enter", "B-exit"]
