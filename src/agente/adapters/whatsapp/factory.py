"""
Fábrica de canal de WhatsApp (RN-40b).

Lê `ChannelConfig.type` e devolve o adapter. Z-API agora; Evolution é o encaixe
pronto para o Clube Amore (self-hosted) — implementar quando alguém pedir.
"""

from agente.adapters.whatsapp.zapi import ZapiWhatsApp
from agente.domain.ports import WhatsAppPort
from agente.domain.tenant import ChannelConfig


def build_channel(config: ChannelConfig) -> WhatsAppPort:
    if config.type == "zapi":
        return ZapiWhatsApp(config)
    if config.type == "evolution":
        raise NotImplementedError(
            "canal 'evolution' ainda não implementado — ver docs/plans/06-canal-zapi.md"
        )
    raise ValueError(
        f"channel.type desconhecido: {config.type!r}. Tipos válidos: 'zapi', 'evolution'."
    )
