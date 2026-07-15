"""
Dispatcher de parsing de entrada por gateway (RN-40b).

Cada canal tem seu formato; aqui escolhemos o parser pelo tipo do canal do
tenant. Todos produzem o mesmo IncomingMessage neutro.
"""

from agente.adapters.whatsapp.zapi_parser import Ignored, parse_zapi
from agente.domain.messaging import IncomingMessage


def parse_incoming(channel_type: str, payload: dict[str, object]) -> IncomingMessage | Ignored:
    if channel_type == "zapi":
        return parse_zapi(payload)
    raise NotImplementedError(
        f"parser do canal {channel_type!r} não implementado (ver plano 06)"
    )
