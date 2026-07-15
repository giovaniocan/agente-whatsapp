"""
E2E do fluxo de conversa: mensagem → LLM (fake, roteirizado) → use cases reais
→ CRM/agenda/WhatsApp. Exercita o motor inteiro com fakes, sem provedor externo.
"""

from collections.abc import Callable
from datetime import date, datetime
from zoneinfo import ZoneInfo

from agente.adapters.crm.fake_crm import FakeCRM
from agente.adapters.llm.fake_llm import FakeLLM
from agente.adapters.scheduler.fake_scheduler import FakeScheduler
from agente.adapters.whatsapp.fake_whatsapp import FakeWhatsApp
from agente.application.assembly import build_handlers
from agente.application.process_message import ProcessIncomingMessage
from agente.domain.conversation import Conversation
from agente.domain.enums import HandoffStatus
from agente.domain.llm import Reply, ToolCall
from agente.domain.tenant import Tenant

SP = ZoneInfo("America/Sao_Paulo")
MONDAY = date(2026, 7, 20)
NOW = datetime(2026, 7, 20, 8, 0, tzinfo=SP)


def _wire(tenant: Tenant, llm: FakeLLM):  # type: ignore[no-untyped-def]
    crm, sched, wpp = FakeCRM(), FakeScheduler(), FakeWhatsApp()
    conv = Conversation(tenant_id=tenant.id, phone="44999998888")
    handlers = build_handlers(tenant, crm, sched, wpp, conv, NOW)
    maestro = ProcessIncomingMessage(tenant, llm, wpp, handlers)
    return maestro, conv, crm, sched, wpp


async def test_full_scheduling_conversation(make_tenant: Callable[..., Tenant]) -> None:
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
            Reply(text="Prontinho, Maria! Agendei sua unha às 11h 🎉"),
        ]
    )
    maestro, conv, crm, sched, wpp = _wire(tenant, llm)

    await maestro.execute(conv, "oi, quero agendar unha segunda às 11")

    # agendamento gravado no CRM
    agenda = await crm.get_scheduled_appointments(MONDAY)
    assert len(agenda) == 1 and agenda[0].intent == "nails"
    # contato criado (sem duplicar)
    assert await crm.find_contact_by_phone("44999998888") is not None
    # 3 lembretes (RN-50)
    assert len([j for j in sched.jobs.values() if j.kind == "reminder"]) == 3
    # resposta final ao cliente
    assert wpp.sent == [("44999998888", "Prontinho, Maria! Agendei sua unha às 11h 🎉")]


async def test_availability_then_reply(make_tenant: Callable[..., Tenant]) -> None:
    tenant = make_tenant()
    llm = FakeLLM(
        [
            ToolCall(name="get_availability", args={"intent": "nails", "day": "2026-07-20"}),
            Reply(text="Tenho vários horários! Qual prefere?"),
        ]
    )
    maestro, conv, crm, sched, wpp = _wire(tenant, llm)

    await maestro.execute(conv, "que horários tem segunda?")

    assert llm.calls == 2   # consulta a tool, depois redige
    assert wpp.sent == [("44999998888", "Tenho vários horários! Qual prefere?")]


async def test_handoff_conversation_silences_ai(
    make_tenant: Callable[..., Tenant],
) -> None:
    tenant = make_tenant()
    # LLM decide escalar; NÃO há Reply na fila — se a IA tentasse responder de
    # novo, o teste estouraria (prova que ela se cala após o handoff).
    llm = FakeLLM([ToolCall(name="escalate_to_human", args={"reason": "explicit_request"})])
    maestro, conv, crm, sched, wpp = _wire(tenant, llm)

    await maestro.execute(conv, "quero falar com um atendente humano")

    assert conv.handoff_status is HandoffStatus.PENDING     # IA parou
    assert len(crm.handoff_tasks) == 1                      # tarefa no CRM
    recipients = [phone for phone, _ in wpp.sent]
    assert "5511999990000" in recipients                   # time avisado
    assert "44999998888" in recipients                     # cliente avisado
    assert llm.calls == 1                                  # não pediu resposta final
    assert any(j.kind == "auto_resume" for j in sched.jobs.values())
