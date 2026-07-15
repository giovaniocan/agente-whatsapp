"""
Use case maestro: processa uma mensagem recebida.

Fluxo: se a IA não está no comando (handoff), cala-se. Senão, pergunta ao LLM;
se ele decide chamar uma ferramenta, despacha para o handler correspondente e
pede ao LLM a resposta final; se ele responde em texto, envia direto.

Os handlers (nome da tool → função) são INJETADOS — a montagem real com os use
cases vive na fase de wiring (planos 06/07). Aqui é só a orquestração.
"""

from collections.abc import Awaitable, Callable, Mapping

from agente.application.tools import build_tool_specs
from agente.domain.conversation import Conversation
from agente.domain.llm import Reply, ToolCall
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
        self._tools = build_tool_specs(tenant)

    async def execute(self, conversation: Conversation, text: str) -> None:
        # RN-31: se não está ACTIVE, a IA não responde (a mensagem seria só
        # armazenada — persistência entra no plano 05).
        if not conversation.can_ai_reply:
            return

        result = await self._llm.respond(conversation, self._tools)

        if isinstance(result, ToolCall):
            await self._dispatch(result)
            # com o resultado em mãos, o LLM redige a resposta final ao cliente.
            result = await self._llm.respond(conversation, self._tools)

        assert isinstance(result, Reply)
        await self._whatsapp.send_text(conversation.phone, result.text)

    async def _dispatch(self, call: ToolCall) -> str:
        handler = self._handlers.get(call.name)
        if handler is None:
            # ferramenta desconhecida ou não permitida (RN-30) — não executa.
            return f"ferramenta indisponível: {call.name}"
        return await handler(call.args)
