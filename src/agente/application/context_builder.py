"""
Montagem econômica de contexto para o LLM (RN-74/75).

Regra de ouro: NUNCA o histórico inteiro. O que vai para o modelo é:
system prompt (estável, cacheável) + tools + resumo rolante + últimas N
mensagens verbatim + a mensagem atual. N vem da ficha (`llm.recent_window`).
"""

from typing import Literal

from agente.application.prompt import build_system_prompt
from agente.application.tools import build_tool_specs
from agente.domain.conversation import Conversation
from agente.domain.llm import LlmMessage, LlmRequest
from agente.domain.messaging import StoredMessage
from agente.domain.tenant import Tenant


def _to_llm_message(m: StoredMessage) -> LlmMessage:
    role: Literal["user", "assistant"] = "user" if m.direction == "in" else "assistant"
    return LlmMessage(role=role, content=m.text)


def build_request(
    tenant: Tenant,
    conversation: Conversation,
    recent_messages: list[StoredMessage],
    current_text: str,
) -> LlmRequest:
    messages: list[LlmMessage] = []

    # RN-75: o resumo entra como contexto no lugar do histórico antigo.
    if conversation.summary:
        messages.append(
            LlmMessage(role="user", content=f"[resumo da conversa até aqui] {conversation.summary}")
        )

    # RN-74: só as últimas N verbatim.
    window = recent_messages[-tenant.llm.recent_window :] if tenant.llm.recent_window else []
    messages.extend(_to_llm_message(m) for m in window)

    messages.append(LlmMessage(role="user", content=current_text))

    return LlmRequest(
        system_prompt=build_system_prompt(tenant),
        messages=messages,
        tools=build_tool_specs(tenant),
    )
