"""Histórico de mensagens — base do summarization buffer (RN-74)."""

from sqlalchemy.ext.asyncio import async_sessionmaker

from agente.adapters.store.postgres_store import PostgresConversationStore


async def test_add_and_fetch_recent_messages(
    sessionmaker: async_sessionmaker,
) -> None:
    store = PostgresConversationStore(sessionmaker)
    await store.add_message("salao", "44999998888", "in", "oi", provider_message_id="M1")
    await store.add_message("salao", "44999998888", "out", "olá! como ajudo?")
    await store.add_message("salao", "44999998888", "in", "quero agendar")

    recent = await store.recent_messages("salao", "44999998888", limit=10)

    # ordem cronológica (mais antiga → mais nova), como o LLM precisa ler
    assert [(m.direction, m.text) for m in recent] == [
        ("in", "oi"),
        ("out", "olá! como ajudo?"),
        ("in", "quero agendar"),
    ]


async def test_recent_messages_respects_limit(sessionmaker: async_sessionmaker) -> None:
    store = PostgresConversationStore(sessionmaker)
    for i in range(5):
        await store.add_message("salao", "44999998888", "in", f"msg{i}")

    recent = await store.recent_messages("salao", "44999998888", limit=2)

    # só as 2 últimas, ainda em ordem cronológica
    assert [m.text for m in recent] == ["msg3", "msg4"]


async def test_history_is_isolated_per_conversation(
    sessionmaker: async_sessionmaker,
) -> None:
    store = PostgresConversationStore(sessionmaker)
    await store.add_message("salao", "44999998888", "in", "da Maria")
    await store.add_message("salao", "11888887777", "in", "do João")

    maria = await store.recent_messages("salao", "44999998888", limit=10)
    assert [m.text for m in maria] == ["da Maria"]
