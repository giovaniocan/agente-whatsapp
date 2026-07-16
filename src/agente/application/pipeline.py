"""
MessagePipeline — a fiação de produção por tenant (Plano 11).

Uma mensagem (já filtrada/deduplicada/agrupada pelo webhook+debounce) passa por:
1. cancela follow-up pendente (o cliente respondeu — RN-51);
2. carrega a conversa e as últimas N mensagens (RN-74);
3. grava a mensagem recebida no histórico;
4. monta canal efetivo: shadow (11.5) → time; sempre gravando o que sai;
5. roda o maestro (LLM + tools);
6. salva a conversa e, se habilitado e a IA segue ativa, agenda novo follow-up.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from agente.adapters.whatsapp.decorators import RecordingChannel, ShadowChannel
from agente.application.assembly import build_handlers
from agente.application.process_message import ProcessIncomingMessage
from agente.domain.ports import (
    ConversationStorePort,
    CRMPort,
    KnowledgePort,
    LLMPort,
    SchedulerPort,
    WhatsAppPort,
)
from agente.domain.tenant import Tenant
from agente.utils.obs import log_event

logger = logging.getLogger(__name__)


class MessagePipeline:
    def __init__(
        self,
        tenant: Tenant,
        store: ConversationStorePort,
        crm: CRMPort,
        scheduler: SchedulerPort,
        llm: LLMPort,
        channel: WhatsAppPort,
        knowledge: KnowledgePort | None = None,
        now_fn: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._tenant = tenant
        self._store = store
        self._crm = crm
        self._scheduler = scheduler
        self._llm = llm
        self._channel = channel
        self._knowledge = knowledge
        self._now_fn = now_fn

    async def handle(self, phone: str, text: str) -> None:
        tenant = self._tenant
        now = self._now_fn()
        correlation = f"followup:{tenant.id}:{phone}"

        # 1. cliente respondeu → follow-up pendente morre (RN-51).
        await self._scheduler.cancel_by_correlation(correlation)

        # 2. conversa + janela de contexto ANTES de gravar a mensagem atual.
        conversation = await self._store.get_or_create(tenant.id, phone)
        recent = await self._store.recent_messages(
            tenant.id, phone, tenant.llm.recent_window
        )

        # 3. registra a entrada no histórico.
        await self._store.add_message(tenant.id, phone, "in", text)

        # 4. canal efetivo: shadow desvia p/ time (11.5); tudo que sai é gravado.
        outbound: WhatsAppPort = self._channel
        if tenant.mode == "shadow":
            outbound = ShadowChannel(outbound, tenant.handoff.team_phone)
        outbound = RecordingChannel(outbound, self._store, tenant.id)

        # 5. maestro.
        handlers = build_handlers(
            tenant, self._crm, self._scheduler, outbound, conversation, now,
            knowledge=self._knowledge,
        )
        await ProcessIncomingMessage(tenant, self._llm, outbound, handlers).execute(
            conversation, text, recent
        )

        # 6. persiste o estado e agenda o próximo follow-up, se fizer sentido.
        await self._store.save(conversation)
        if tenant.follow_up.enabled and conversation.can_ai_reply:
            await self._scheduler.schedule(
                "follow_up",
                now + timedelta(hours=tenant.follow_up.delay_hours),
                {
                    "tenant_id": tenant.id,
                    "phone": phone,
                    "message": tenant.follow_up.message,
                },
                correlation_id=correlation,
            )

        log_event(
            logger, "message_processed",
            tenant_id=tenant.id, phone=phone, mode=tenant.mode,
            handoff=conversation.handoff_status.value,
        )
