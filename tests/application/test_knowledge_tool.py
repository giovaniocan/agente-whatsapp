"""Tool search_knowledge no assembly (Plano 10.3)."""

from collections.abc import Callable
from datetime import UTC, datetime

from agente.adapters.crm.fake_crm import FakeCRM
from agente.adapters.scheduler.fake_scheduler import FakeScheduler
from agente.adapters.whatsapp.fake_whatsapp import FakeWhatsApp
from agente.application.assembly import build_handlers
from agente.domain.conversation import Conversation
from agente.domain.tenant import Tenant

NOW = datetime(2026, 7, 20, 8, 0, tzinfo=UTC)


class _FakeKnowledge:
    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks
        self.queries: list[tuple[str, str]] = []

    async def search(self, tenant_id: str, query: str, k: int = 5) -> list[str]:
        self.queries.append((tenant_id, query))
        return self._chunks


def _handlers(make_tenant: Callable[..., Tenant], knowledge: object):  # type: ignore[no-untyped-def]
    tenant = make_tenant()
    conv = Conversation(tenant_id=tenant.id, phone="44999998888")
    return tenant, build_handlers(
        tenant, FakeCRM(), FakeScheduler(), FakeWhatsApp(), conv, NOW,
        knowledge=knowledge,  # type: ignore[arg-type]
    )


async def test_search_knowledge_returns_chunks_scoped_to_tenant(
    make_tenant: Callable[..., Tenant],
) -> None:
    kb = _FakeKnowledge(["Unha em gel dura até 60 minutos."])
    tenant, handlers = _handlers(make_tenant, kb)

    result = await handlers["search_knowledge"]({"query": "quanto demora unha em gel?"})

    assert "60 minutos" in result
    assert kb.queries == [(tenant.id, "quanto demora unha em gel?")]   # escopo do tenant


async def test_empty_base_instructs_not_to_invent(
    make_tenant: Callable[..., Tenant],
) -> None:
    _, handlers = _handlers(make_tenant, _FakeKnowledge([]))
    result = await handlers["search_knowledge"]({"query": "tem promoção?"})
    assert "não invente" in result                     # reforço da RN-30


async def test_missing_knowledge_store_degrades_gracefully(
    make_tenant: Callable[..., Tenant],
) -> None:
    _, handlers = _handlers(make_tenant, None)
    result = await handlers["search_knowledge"]({"query": "qualquer"})
    assert "indisponível" in result
