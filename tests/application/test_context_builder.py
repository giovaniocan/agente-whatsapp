"""Montagem econômica de contexto para o LLM (Plano 07.3b, RN-74)."""

from collections.abc import Callable

from agente.application.context_builder import build_request
from agente.domain.conversation import Conversation
from agente.domain.messaging import StoredMessage
from agente.domain.tenant import Tenant


def _history(n: int) -> list[StoredMessage]:
    out: list[StoredMessage] = []
    for i in range(n):
        out.append(StoredMessage(direction="in", text=f"in{i}"))
        out.append(StoredMessage(direction="out", text=f"out{i}"))
    return out


def test_request_carries_system_prompt_and_tools(
    make_tenant: Callable[..., Tenant],
) -> None:
    tenant = make_tenant()
    conv = Conversation(tenant_id=tenant.id, phone="44999998888")
    req = build_request(tenant, conv, recent_messages=[], current_text="oi")

    assert "Bia" in req.system_prompt          # veio da ficha
    assert req.tools                           # ferramentas anexadas
    assert req.messages[-1].content == "oi"    # mensagem atual por último


def test_only_last_n_messages_are_sent(make_tenant: Callable[..., Tenant]) -> None:
    # RN-74: nunca o histórico inteiro — só as últimas N (recent_window).
    tenant = make_tenant()
    tenant = tenant.model_copy(update={"llm": tenant.llm.model_copy(update={"recent_window": 4})})
    conv = Conversation(tenant_id=tenant.id, phone="44999998888")

    req = build_request(tenant, conv, recent_messages=_history(50), current_text="agora")

    # 4 do histórico + a atual = 5, e não 101.
    assert len(req.messages) == 5
    assert req.messages[-1].content == "agora"
    assert [m.content for m in req.messages[:-1]] == ["in48", "out48", "in49", "out49"]


def test_summary_is_included_when_present(make_tenant: Callable[..., Tenant]) -> None:
    # RN-75: o resumo rolante entra no lugar do histórico antigo.
    tenant = make_tenant()
    conv = Conversation(
        tenant_id=tenant.id, phone="44999998888", summary="cliente quer unha em gel"
    )
    req = build_request(tenant, conv, recent_messages=[], current_text="oi")

    assert any("unha em gel" in m.content for m in req.messages)


def test_roles_map_direction(make_tenant: Callable[..., Tenant]) -> None:
    tenant = make_tenant()
    conv = Conversation(tenant_id=tenant.id, phone="44999998888")
    req = build_request(tenant, conv, recent_messages=_history(1), current_text="oi")

    # "in" -> user, "out" -> assistant
    roles = [m.role for m in req.messages]
    assert roles == ["user", "assistant", "user"]
