"""MessagePipeline (Plano 11) — a fiação de produção, testada com fakes."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from agente.adapters.crm.fake_crm import FakeCRM
from agente.adapters.llm.fake_llm import FakeLLM
from agente.adapters.scheduler.fake_scheduler import FakeScheduler
from agente.adapters.store.fake_store import FakeConversationStore
from agente.adapters.whatsapp.fake_whatsapp import FakeWhatsApp
from agente.application.pipeline import MessagePipeline
from agente.domain.llm import Reply
from agente.domain.tenant import FollowUpConfig, HandoffConfig, Tenant

NOW = datetime(2026, 7, 20, 11, 0, tzinfo=UTC)


def _pipeline(tenant: Tenant):  # type: ignore[no-untyped-def]
    store, sched, wpp = FakeConversationStore(), FakeScheduler(), FakeWhatsApp()
    llm = FakeLLM([Reply(text="Olá! Posso ajudar?")])
    pipe = MessagePipeline(
        tenant=tenant,
        store=store,
        crm=FakeCRM(),
        scheduler=sched,
        llm=llm,
        channel=wpp,
        now_fn=lambda: NOW,
    )
    return pipe, store, sched, wpp


async def test_records_history_and_replies(make_tenant: Callable[..., Tenant]) -> None:
    pipe, store, _, wpp = _pipeline(make_tenant())

    await pipe.handle("44999998888", "oi")

    history = await store.recent_messages("salao", "44999998888", limit=10)
    assert [(m.direction, m.text) for m in history] == [
        ("in", "oi"),
        ("out", "Olá! Posso ajudar?"),
    ]
    assert wpp.sent == [("44999998888", "Olá! Posso ajudar?")]


async def test_follow_up_scheduled_after_reply_and_cancelled_on_next_message(
    make_tenant: Callable[..., Tenant],
) -> None:
    tenant = make_tenant(
        follow_up=FollowUpConfig(enabled=True, delay_hours=4, message="Ainda aí?")
    )
    pipe, store, sched, _ = _pipeline(tenant)

    await pipe.handle("44999998888", "oi")

    jobs = [j for j in sched.jobs.values() if j.kind == "follow_up"]
    assert len(jobs) == 1
    assert jobs[0].run_at == NOW + timedelta(hours=4)
    assert jobs[0].payload["message"] == "Ainda aí?"

    # cliente respondeu → follow-up antigo é cancelado (e um novo entra)
    pipe._llm._queue.append(Reply(text="Perfeito!"))  # type: ignore[attr-defined]
    await pipe.handle("44999998888", "quero agendar")
    jobs = [j for j in sched.jobs.values() if j.kind == "follow_up"]
    assert len(jobs) == 1                              # só o novo


async def test_shadow_mode_routes_reply_to_team(
    make_tenant: Callable[..., Tenant],
) -> None:
    tenant = make_tenant(
        mode="shadow", handoff=HandoffConfig(team_phone="5511999990000")
    )
    pipe, store, _, wpp = _pipeline(tenant)

    await pipe.handle("44999998888", "oi")

    [(to, text)] = wpp.sent
    assert to == "5511999990000"                       # cliente NÃO recebeu
    assert "44999998888" in text and "Olá! Posso ajudar?" in text
