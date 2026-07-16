"""
Decoradores de WhatsAppPort (Plano 11).

- ShadowChannel (11.5): piloto em shadow mode — toda mensagem que iria ao
  CLIENTE é redirecionada ao time como sugestão. A IA nunca fala com o cliente
  até o tenant virar "autonomous".
- RecordingChannel: grava cada mensagem enviada no histórico da conversa
  (alimenta o buffer de contexto do LLM, RN-74).

São composáveis: RecordingChannel(ShadowChannel(zapi, ...), store, ...).
"""

from agente.domain.ports import ConversationStorePort, WhatsAppPort


class ShadowChannel:
    def __init__(self, inner: WhatsAppPort, team_phone: str) -> None:
        self._inner = inner
        self._team_phone = team_phone

    async def send_text(self, phone: str, text: str) -> None:
        suggestion = f"[SHADOW — sugestão p/ {phone}]\n{text}"
        await self._inner.send_text(self._team_phone, suggestion)


class RecordingChannel:
    def __init__(
        self, inner: WhatsAppPort, store: ConversationStorePort, tenant_id: str
    ) -> None:
        self._inner = inner
        self._store = store
        self._tenant_id = tenant_id

    async def send_text(self, phone: str, text: str) -> None:
        await self._inner.send_text(phone, text)
        await self._store.add_message(self._tenant_id, phone, "out", text)
