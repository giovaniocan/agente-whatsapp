"""
Modelos que CRUZAM a porta de CRM — o vocabulário limpo do nosso domínio.

Regra de ouro do Anti-Corruption Layer (ACL): nenhum nome do Trivus aparece
aqui. Nada de `crm_funnel_leads`, `data_agendamento`, `qualificado`. Estes são
OS NOSSOS tipos, em inglês. Quem traduz Trivus <-> estes tipos é o adaptador
(adapters/crm/trivus.py), e só ele.
"""

from datetime import datetime

from pydantic import BaseModel

from agente.domain.enums import (
    AppointmentStatus,
    EscalationTrigger,
    LeadPriority,
    ServiceIntent,
)


class Contact(BaseModel):
    """Uma pessoa já GRAVADA no CRM (o lead persistido)."""
    id: str                                     # id do CRM, tratado como string na nossa borda
    full_name: str
    phone: str
    email: str | None = None
    intent: ServiceIntent | None = None         # pode não estar qualificado ainda
    priority: LeadPriority = LeadPriority.MEDIUM
    notes: str | None = None


class AvailableSlot(BaseModel):
    """
    Um horário livre. CALCULADO pelo agente a partir da SchedulingPolicy do
    tenant (o Trivus não fornece isto). `start`/`end` são datetime COM fuso.
    """
    start: datetime
    end: datetime


class AppointmentRequest(BaseModel):
    """Pedido para agendar — o que o agente entrega à porta."""
    contact_id: str
    intent: ServiceIntent                       # comprar/vender define o "serviço"
    start: datetime
    notes: str | None = None


class Appointment(BaseModel):
    """Agendamento confirmado — o que a porta devolve."""
    id: str
    contact_id: str
    start: datetime
    end: datetime
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
