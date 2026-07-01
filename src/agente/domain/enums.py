from enum import StrEnum


class ServiceIntent(StrEnum):
    BUY = "buy"
    SELL = "sell"


class AvailabilityMode(StrEnum):
    ALWAYS_ON        = "24_7"
    BUSINESS_HOURS   = "business_hours"
    AFTER_HOURS      = "after_hours"
    WEEKENDS_ONLY    = "weekends_only"

class LeadPriority(StrEnum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"


class EscalationTrigger(StrEnum):
    EXPLICIT_REQUEST    = "explicit_request"
    DISSATISFACTION     = "dissatisfaction"
    PERSISTENT_CONFUSION = "persistent_confusion"
    OUT_OF_RULES        = "out_of_rules"
    RETENTION_RISK      = "retention_risk"


class HandoffStatus(StrEnum):
    # Estado da conversa quanto ao "quem responde agora".
    ACTIVE  = "active"    # a IA está no comando, respondendo normalmente
    PENDING = "pending"   # escalou: a IA parou, aguardando um humano assumir
    HUMAN   = "human"     # um humano assumiu de fato a conversa


class AppointmentStatus(StrEnum):
    # Ciclo de vida de um agendamento (conceito do NOSSO domínio;
    # o Trivus não tem agendamento como entidade própria).
    SCHEDULED   = "scheduled"
    CANCELLED   = "cancelled"
    RESCHEDULED = "rescheduled"