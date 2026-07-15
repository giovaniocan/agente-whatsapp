"""
Mensagem de entrada NEUTRA de canal (RN-40b).

Todo gateway (Z-API, Evolution…) tem um parser próprio que produz este mesmo
tipo. O motor só conhece o IncomingMessage — nunca o formato do gateway.
"""

from pydantic import BaseModel


class IncomingMessage(BaseModel):
    text: str
    message_id: str
    phone: str | None = None       # número normalizado (sem DDI 55), quando houver
    lid: str | None = None         # id anônimo do WhatsApp, quando o número é privado
    sender_name: str | None = None


class StoredMessage(BaseModel):
    # Um turno do histórico (para o buffer de contexto do LLM, RN-74).
    direction: str                 # "in" (cliente) | "out" (agente)
    text: str
