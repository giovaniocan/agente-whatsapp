"""
E2E de ponta a ponta REAL: request HTTP no webhook → parser Z-API → dedupe →
maestro → use cases → CRM/agenda/WhatsApp. Só os provedores externos são fakes.
"""

from collections.abc import Callable
from datetime import date, datetime
from zoneinfo import ZoneInfo

from httpx import ASGITransport, AsyncClient

from agente.adapters.crm.fake_crm import FakeCRM
from agente.adapters.llm.fake_llm import FakeLLM
from agente.adapters.scheduler.fake_scheduler import FakeScheduler
from agente.adapters.store.fake_store import FakeConversationStore
from agente.adapters.whatsapp.fake_whatsapp import FakeWhatsApp
from agente.api.webhook import create_app
from agente.application.assembly import build_handlers
from agente.application.process_message import ProcessIncomingMessage
from agente.domain.llm import Reply, ToolCall
from agente.domain.messaging import IncomingMessage
from agente.domain.tenant import Tenant

SP = ZoneInfo("America/Sao_Paulo")
MONDAY = date(2026, 7, 20)
NOW = datetime(2026, 7, 20, 8, 0, tzinfo=SP)


def _zapi_text(**over: object) -> dict:
    data: dict[str, object] = {
        "phone": "5544999998888",
        "chatName": "Maria",
        "messageId": "MSG-1",
        "text": {"message": "quero agendar unha segunda 11h"},
    }
    data.update(over)
    return data


def _build_app(tenant: Tenant, llm: FakeLLM):  # type: ignore[no-untyped-def]
    crm, sched, wpp = FakeCRM(), FakeScheduler(), FakeWhatsApp()
    store = FakeConversationStore()

    async def processor(t: Tenant, incoming: IncomingMessage) -> None:
        phone = incoming.phone or incoming.lid or ""
        conv = await store.get_or_create(t.id, phone)
        handlers = build_handlers(t, crm, sched, wpp, conv, NOW)
        await ProcessIncomingMessage(t, llm, wpp, handlers).execute(conv, incoming.text)

    app = create_app(
        registry={tenant.webhook_token: tenant}, store=store, processor=processor
    )
    return app, crm, wpp


def _client(app: object) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")  # type: ignore[arg-type]


async def test_webhook_message_results_in_scheduled_appointment_and_reply(
    make_tenant: Callable[..., Tenant],
) -> None:
    tenant = make_tenant()
    llm = FakeLLM(
        [
            ToolCall(
                name="schedule_appointment",
                args={
                    "full_name": "Maria Souza",
                    "intent": "nails",
                    "start": "2026-07-20T11:00:00-03:00",
                },
            ),
            Reply(text="Agendado, Maria! Te espero segunda às 11h 🎉"),
        ]
    )
    app, crm, wpp = _build_app(tenant, llm)

    async with _client(app) as client:
        resp = await client.post("/webhook/whatsapp/TKN-salao", json=_zapi_text())

    assert resp.status_code == 200
    # o processamento em background rodou o fluxo inteiro:
    agenda = await crm.get_scheduled_appointments(MONDAY)
    assert len(agenda) == 1
    assert wpp.sent[-1] == ("44999998888", "Agendado, Maria! Te espero segunda às 11h 🎉")


async def test_duplicate_webhook_delivery_schedules_once(
    make_tenant: Callable[..., Tenant],
) -> None:
    # RN-42: reentrega do webhook (mesmo messageId) não agenda duas vezes.
    tenant = make_tenant()
    llm = FakeLLM(
        [
            ToolCall(
                name="schedule_appointment",
                args={
                    "full_name": "Maria Souza",
                    "intent": "nails",
                    "start": "2026-07-20T11:00:00-03:00",
                },
            ),
            Reply(text="Agendado!"),
        ]
    )
    app, crm, wpp = _build_app(tenant, llm)

    async with _client(app) as client:
        await client.post("/webhook/whatsapp/TKN-salao", json=_zapi_text())
        await client.post("/webhook/whatsapp/TKN-salao", json=_zapi_text())  # reentrega

    agenda = await crm.get_scheduled_appointments(MONDAY)
    assert len(agenda) == 1   # não duplicou
