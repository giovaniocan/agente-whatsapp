"""ProcessIncomingMessage — o maestro (Plano 04.6). Fecha o M1."""

from collections.abc import Callable

from agente.adapters.llm.fake_llm import FakeLLM
from agente.adapters.whatsapp.fake_whatsapp import FakeWhatsApp
from agente.application.process_message import ProcessIncomingMessage
from agente.application.tools import FORBIDDEN_TOOLS, build_tool_specs
from agente.domain.conversation import Conversation
from agente.domain.llm import Reply, ToolCall
from agente.domain.tenant import Tenant


def _conv() -> Conversation:
    return Conversation(tenant_id="salao", phone="44999998888")


def test_toolset_never_exposes_forbidden_tools(
    make_tenant: Callable[..., Tenant],
) -> None:
    # RN-30: fronteira humana por design — sem preço/desconto/financiamento.
    names = {spec.name for spec in build_tool_specs(make_tenant())}
    assert names.isdisjoint(FORBIDDEN_TOOLS)


async def test_ai_stays_silent_when_not_active(
    make_tenant: Callable[..., Tenant],
) -> None:
    conv = _conv()
    conv.request_handoff()   # PENDING
    llm, wpp = FakeLLM([Reply(text="não deveria falar")]), FakeWhatsApp()
    maestro = ProcessIncomingMessage(make_tenant(), llm, wpp, handlers={})

    await maestro.execute(conv, "oi")

    assert wpp.sent == []       # IA calada
    assert llm.calls == 0       # nem chamou o LLM


async def test_plain_reply_is_sent(make_tenant: Callable[..., Tenant]) -> None:
    conv = _conv()
    llm, wpp = FakeLLM([Reply(text="Olá! Como posso ajudar?")]), FakeWhatsApp()
    maestro = ProcessIncomingMessage(make_tenant(), llm, wpp, handlers={})

    await maestro.execute(conv, "oi")

    assert wpp.sent == [("44999998888", "Olá! Como posso ajudar?")]


async def test_tool_call_is_dispatched_then_final_reply_sent(
    make_tenant: Callable[..., Tenant],
) -> None:
    conv = _conv()
    invoked: dict[str, dict] = {}

    async def schedule_handler(args: dict) -> str:
        invoked["args"] = args
        return "ok, agendado às 11h"

    llm = FakeLLM(
        [
            ToolCall(name="schedule_appointment", args={"start": "2026-07-20T11:00"}),
            Reply(text="Prontinho, agendei às 11h! 🎉"),
        ]
    )
    wpp = FakeWhatsApp()
    maestro = ProcessIncomingMessage(
        make_tenant(), llm, wpp, handlers={"schedule_appointment": schedule_handler}
    )

    await maestro.execute(conv, "quero agendar 11h")

    assert invoked["args"] == {"start": "2026-07-20T11:00"}   # handler chamado
    assert wpp.sent == [("44999998888", "Prontinho, agendei às 11h! 🎉")]
    assert llm.calls == 2   # 1ª decide a tool, 2ª redige a resposta final
