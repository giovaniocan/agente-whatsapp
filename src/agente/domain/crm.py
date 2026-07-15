"""
Modelos que CRUZAM a porta de CRM — o vocabulário limpo do nosso domínio.

Regra de ouro do Anti-Corruption Layer (ACL): nenhum nome do Trivus aparece
aqui. Nada de `crm_funnel_leads`, `data_agendamento`, `qualificado`. Estes são
OS NOSSOS tipos, em inglês. Quem traduz Trivus <-> estes tipos é o adaptador
(adapters/crm/trivus.py), e só ele.
"""

from pydantic import AwareDatetime, BaseModel

from agente.domain.enums import (
    AppointmentStatus,
    EscalationTrigger,
    LeadPriority,
)


class Contact(BaseModel):
    """Uma pessoa já GRAVADA no CRM (o lead persistido)."""
    id: str                                     # id do CRM, tratado como string na nossa borda
    full_name: str
    phone: str
    email: str | None = None
    intent: str | None = None                   # RN-02; None se não qualificado ainda
    priority: LeadPriority = LeadPriority.MEDIUM
    notes: str | None = None


class AvailableSlot(BaseModel):
    """
    Um horário livre. CALCULADO pelo agente a partir da SchedulingPolicy do
    tenant (o Trivus não fornece isto). `start`/`end` são datetime COM fuso.
    """
    start: AwareDatetime
    end: AwareDatetime


class AppointmentRequest(BaseModel):
    """Pedido para agendar — o que o agente entrega à porta.

    Carrega o intervalo completo (start+end): o use case calcula `end` a partir
    da duração do serviço; o CRM só persiste, não conhece durações.
    """
    contact_id: str
    intent: str                                 # RN-02: a intent define o "serviço"
    start: AwareDatetime
    end: AwareDatetime
    notes: str | None = None


class Appointment(BaseModel):
    """Agendamento confirmado — o que a porta devolve."""
    id: str
    contact_id: str
    intent: str                                 # RN-11: casa ocupação por serviço
    start: AwareDatetime
    end: AwareDatetime
    status: AppointmentStatus = AppointmentStatus.SCHEDULED


class HandoffTask(BaseModel):
    """
    Pacote de escalonamento para um humano. No futuro TrivusCRM isto vira
    `assigned_to` (atribuir o lead) + um registro em `crm_activity_log`.
    """
    contact_id: str
    reason: EscalationTrigger                    # por que escalou
    priority: LeadPriority
    context: str                                 # resumo da conversa + dados do lead
    routing_hint: str | None = None              # ex.: "time de vendas", ou id de vendedor
