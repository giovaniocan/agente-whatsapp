"""
Use case maestro: processa uma mensagem recebida.

Fluxo: se a IA não está no comando (handoff), cala-se. Senão, monta o contexto
econômico (RN-74), pergunta ao LLM; se ele decide chamar uma ferramenta,
despacha para o handler e pede a resposta final; se responde em texto, envia.

Os handlers (nome da tool → função) são INJETADOS — a montagem real com os use
cases vive na fase de wiring. Aqui é só a orquestração.
"""

from collections.abc import Awaitable, Callable, Mapping

from agente.application.context_builder import build_request
from agente.domain.conversation import Conversation
from agente.domain.llm import Reply, ToolCall
from agente.domain.messaging import StoredMessage
from agente.domain.ports import LLMPort, WhatsAppPort
from agente.domain.tenant import Tenant

ToolHandler = Callable[[dict[str, object]], Awaitable[str]]


class ProcessIncomingMessage:
    def __init__(
        self,
        tenant: Tenant,
        llm: LLMPort,
        whatsapp: WhatsAppPort,
        handlers: Mapping[str, ToolHandler],
    ) -> None:
        self._tenant = tenant
        self._llm = llm
        self._whatsapp = whatsapp
        self._handlers = handlers

    async def execute(
        self,
        conversation: Conversation,
        text: str,
        recent_messages: list[StoredMessage] | None = None,
    ) -> None:
        # RN-31: se não está ACTIVE, a IA não responde.
        if not conversation.can_ai_reply:
            return

        request = build_request(
            self._tenant, conversation, recent_messages or [], text
        )
        result = await self._llm.respond(request)

        if isinstance(result, ToolCall):
            await self._dispatch(result)
            # se a ferramenta escalou para humano, a mensagem ao cliente já foi
            # enviada pelo use case — a IA não fala mais (RN-31).
            if not conversation.can_ai_reply:
                return
            # com o resultado em mãos, o LLM redige a resposta final ao cliente.
            result = await self._llm.respond(request)

        assert isinstance(result, Reply)
        await self._whatsapp.send_text(conversation.phone, result.text)

    async def _dispatch(self, call: ToolCall) -> str:
        handler = self._handlers.get(call.name)
        if handler is None:
            # ferramenta desconhecida ou não permitida (RN-30) — não executa.
            return f"ferramenta indisponível: {call.name}"
        return await handler(call.args)
