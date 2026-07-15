"""
Handlers dos jobs do worker (Plano 09).

- reminder    (RN-50): manda o lembrete do agendamento no fuso do tenant.
- auto_resume (RN-31.6): devolve o comando à IA se nenhum humano assumiu.
- follow_up   (RN-51): cutuca lead frio — só se a IA ainda está no comando.

Recebem o registry de tenants + store + fábrica de canal; devolvem o mapa
{kind -> handler} que o JobWorker consome. Tenant desconhecido = KeyError
(job vira `failed`, visível — nunca engolimos o erro).
"""

from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from agente.domain.enums import HandoffStatus
from agente.domain.ports import ConversationStorePort, WhatsAppPort
from agente.domain.tenant import Tenant

JobHandler = Callable[[dict[str, Any]], Awaitable[None]]
ChannelFactory = Callable[[Tenant], WhatsAppPort]


def build_job_handlers(
    registry: Mapping[str, Tenant],
    store: ConversationStorePort,
    channel_for: ChannelFactory,
) -> dict[str, JobHandler]:
    def _tenant(payload: dict[str, Any]) -> Tenant:
        return registry[str(payload["tenant_id"])]   # KeyError = job failed (visível)

    async def reminder(payload: dict[str, Any]) -> None:
        tenant = _tenant(payload)
        start = datetime.fromisoformat(str(payload["start"]))
        local = start.astimezone(ZoneInfo(tenant.scheduling.timezone))
        text = (
            f"Oi! Lembrete do seu horário em {tenant.name}: "
            f"{local.strftime('%d/%m às %H:%M')} 🙂"
        )
        await channel_for(tenant).send_text(str(payload["phone"]), text)

    async def auto_resume(payload: dict[str, Any]) -> None:
        tenant = _tenant(payload)
        conv = await store.get_or_create(tenant.id, str(payload["phone"]))
        # Só retoma se ainda está PENDENTE; humano no comando = no-op (RN-31.6).
        if conv.handoff_status is HandoffStatus.PENDING:
            conv.resume()
            await store.save(conv)

    async def follow_up(payload: dict[str, Any]) -> None:
        tenant = _tenant(payload)
        conv = await store.get_or_create(tenant.id, str(payload["phone"]))
        if not conv.can_ai_reply:
            return                                   # handoff em curso: não cutuca
        await channel_for(tenant).send_text(
            str(payload["phone"]), str(payload["message"])
        )

    return {"reminder": reminder, "auto_resume": auto_resume, "follow_up": follow_up}
