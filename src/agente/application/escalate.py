"""
Use case: escalar a conversa para um humano (RN-31), NA ORDEM.

1. status = PENDING (a IA para ANTES de qualquer I/O)
2. monta o pacote de contexto
3. cria a tarefa no CRM
4. notifica o time
5. envia a mensagem de handoff ao cliente
6. agenda o auto-resume

Fallback: se (3) falhar, o time é notificado mesmo assim e a IA permanece
PENDING — nunca deixamos a IA voltar sozinha por causa de um erro de I/O.
"""

import logging
from datetime import datetime, timedelta

from agente.domain.conversation import Conversation
from agente.domain.crm import HandoffTask
from agente.domain.enums import EscalationTrigger, LeadPriority
from agente.domain.ports import CRMPort, SchedulerPort, WhatsAppPort
from agente.domain.tenant import Tenant

logger = logging.getLogger(__name__)


class EscalateToHuman:
    def __init__(
        self,
        tenant: Tenant,
        crm: CRMPort,
        whatsapp: WhatsAppPort,
        scheduler: SchedulerPort,
    ) -> None:
        self._tenant = tenant
        self._crm = crm
        self._whatsapp = whatsapp
        self._scheduler = scheduler

    async def execute(
        self,
        conversation: Conversation,
        contact_id: str,
        reason: EscalationTrigger,
        now: datetime,
        routing_hint: str | None = None,
    ) -> None:
        # (1) a IA para imediatamente, antes de qualquer I/O.
        conversation.request_handoff()

        # (2) pacote de contexto.
        priority = (
            conversation.lead_draft.priority
            if conversation.lead_draft is not None
            else LeadPriority.MEDIUM
        )
        task = HandoffTask(
            contact_id=contact_id,
            reason=reason,
            priority=priority,
            context=self._build_context(conversation, reason),
            routing_hint=routing_hint,
        )

        # (3) tarefa no CRM — se falhar, seguimos (o time PRECISA ser avisado).
        try:
            await self._crm.create_handoff_task(task)
        except Exception:
            logger.exception("falha ao criar handoff task no CRM; notificando time assim mesmo")

        # (4) notifica o time.
        if self._tenant.handoff.team_phone:
            await self._whatsapp.send_text(
                self._tenant.handoff.team_phone,
                f"🔔 Handoff ({reason.value}) — {conversation.phone}",
            )

        # (5) mensagem ao cliente.
        await self._whatsapp.send_text(conversation.phone, self._tenant.handoff.message)

        # (6) auto-resume.
        run_at = now + timedelta(hours=self._tenant.handoff.auto_resume_hours)
        await self._scheduler.schedule(
            "auto_resume",
            run_at,
            {"tenant_id": conversation.tenant_id, "phone": conversation.phone},
            correlation_id=f"resume:{conversation.tenant_id}:{conversation.phone}",
        )

    def _build_context(
        self, conversation: Conversation, reason: EscalationTrigger
    ) -> str:
        lines = [f"Motivo: {reason.value}", f"Resumo: {conversation.summary}"]
        if conversation.lead_draft is not None:
            lines.append(f"Lead: {conversation.lead_draft.model_dump_json()}")
        return "\n".join(lines)
