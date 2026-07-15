"""
Portas do domínio — os contratos que os adapters cumprem (hexagonal).

Tudo é `Protocol` (subtipagem estrutural: quem tiver os métodos, serve — sem
herança) e async (RN-65). O domínio/aplicação falam SÓ com estas interfaces;
as implementações vivem em `adapters/`. Assinaturas usam tipos do domínio —
nenhum vocabulário externo aqui (RN-60).
"""

from contextlib import AbstractAsyncContextManager
from datetime import date, datetime
from typing import Any, Protocol, runtime_checkable

from agente.domain.conversation import Conversation
from agente.domain.crm import Appointment, AppointmentRequest, Contact, HandoffTask
from agente.domain.enums import LeadPriority
from agente.domain.llm import Reply, ToolCall, ToolSpec


@runtime_checkable
class CRMPort(Protocol):
    """Integração com o CRM do tenant (FakeCRM agora; TrivusCRM/ClubeAmore depois)."""

    async def find_contact_by_phone(self, phone: str) -> Contact | None: ...

    async def create_contact(
        self, full_name: str, phone: str, email: str | None = None
    ) -> Contact: ...

    async def update_lead_qualification(
        self,
        contact_id: str,
        intent: str,
        priority: LeadPriority,
        notes: str | None = None,
    ) -> None: ...

    async def get_scheduled_appointments(self, day: date) -> list[Appointment]: ...

    async def create_appointment(self, request: AppointmentRequest) -> Appointment: ...

    async def cancel_appointment(self, appointment_id: str) -> None: ...

    async def get_appointment(self, appointment_id: str) -> Appointment | None: ...

    async def reschedule_appointment(
        self, appointment_id: str, new_start: datetime
    ) -> Appointment: ...

    # TODO(TrivusCRM): sem tabela de tarefa no Trivus — implementar como
    # assigned_to + registro em crm_activity_log (ver plano 08).
    async def create_handoff_task(self, task: HandoffTask) -> None: ...


@runtime_checkable
class WhatsAppPort(Protocol):
    """Canal de saída (Z-API agora; Evolution depois, RN-40b)."""

    async def send_text(self, phone: str, text: str) -> None: ...


class ConversationStorePort(Protocol):
    """Persistência do estado de conversa + dedupe de mensagem (RN-42)."""

    async def get_or_create(self, tenant_id: str, phone: str) -> Conversation: ...

    async def save(self, conversation: Conversation) -> None: ...

    async def mark_message_seen(self, provider_message_id: str) -> bool:
        """True se já vista (ignorar); False se é nova. Idempotência do webhook."""
        ...

    def lock(self, key: str) -> AbstractAsyncContextManager[None]:
        """Lock por conversa (RN-44): serializa o processamento do mesmo telefone."""
        ...


class SchedulerPort(Protocol):
    """Agenda jobs (lembretes, auto-resume, follow-up) — RN-50/RN-51/RN-31.

    `correlation_id` agrupa jobs de uma mesma entidade (ex.: agendamento), para
    cancelá-los em bloco quando ela muda (reagendar/cancelar recalcula lembretes).
    """

    async def schedule(
        self,
        kind: str,
        run_at: datetime,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> str: ...

    async def cancel(self, job_id: str) -> None: ...

    async def cancel_by_correlation(self, correlation_id: str) -> None: ...


class KnowledgePort(Protocol):
    """Base de conhecimento por tenant (RAG) — RN-01/plano 10."""

    async def search(self, tenant_id: str, query: str, k: int = 5) -> list[str]: ...


class LLMPort(Protocol):
    """Cérebro plugável (RN-70/RN-71). Refinada no plano 07."""

    async def respond(
        self, conversation: Conversation, tools: list[ToolSpec]
    ) -> Reply | ToolCall: ...
