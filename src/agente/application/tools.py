"""
Catálogo de ferramentas oferecidas ao LLM (neutro — RN-71).

Fronteira humana POR DESIGN (RN-30): a lista de ferramentas permitidas NUNCA
inclui preço, desconto, negociação, financiamento ou fechamento de contrato.
O modelo não pode fazer o que não tem ferramenta para fazer.

Os ToolSpec carregam JSON Schema puro — sem nada específico de provedor. Cada
adapter de LLM traduz para o formato do provedor dele (Anthropic, OpenAI, …).
As intents vêm da ficha do tenant (RN-02).
"""

from agente.domain.enums import EscalationTrigger, LeadPriority
from agente.domain.llm import ToolSpec
from agente.domain.tenant import Tenant

# Ações que o agente PODE executar.
ALLOWED_TOOLS: list[str] = [
    "get_availability",
    "schedule_appointment",
    "reschedule_appointment",
    "cancel_appointment",
    "qualify_lead",
    "escalate_to_human",
]

# Ações que o agente NUNCA executa (não existem como ferramenta) — RN-30.
FORBIDDEN_TOOLS: list[str] = [
    "apply_discount",
    "set_price",
    "negotiate_value",
    "handle_financing",
    "close_contract",
]


def _str(desc: str) -> dict[str, object]:
    return {"type": "string", "description": desc}


def _obj(properties: dict[str, object], required: list[str]) -> dict[str, object]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def build_tool_specs(tenant: Tenant) -> list[ToolSpec]:
    intents = list(tenant.intents)                       # RN-02
    priorities = [p.value for p in LeadPriority]
    reasons = [r.value for r in EscalationTrigger]

    intent_prop = {"type": "string", "enum": intents, "description": "serviço/intenção"}

    return [
        ToolSpec(
            name="get_availability",
            description="Lista horários livres para um serviço num dia.",
            parameters=_obj(
                {"intent": intent_prop, "day": _str("dia no formato YYYY-MM-DD")},
                ["intent", "day"],
            ),
        ),
        ToolSpec(
            name="schedule_appointment",
            description="Agenda um atendimento em um horário livre.",
            parameters=_obj(
                {
                    "intent": intent_prop,
                    "full_name": _str("nome completo do cliente"),
                    "start": _str("início no formato ISO 8601 com fuso"),
                    "notes": _str("observações (opcional)"),
                },
                ["intent", "full_name", "start"],
            ),
        ),
        ToolSpec(
            name="reschedule_appointment",
            description="Move um agendamento para outro horário.",
            parameters=_obj(
                {
                    "appointment_id": _str("id do agendamento"),
                    "new_start": _str("novo início ISO 8601 com fuso"),
                },
                ["appointment_id", "new_start"],
            ),
        ),
        ToolSpec(
            name="cancel_appointment",
            description="Cancela um agendamento.",
            parameters=_obj(
                {"appointment_id": _str("id do agendamento")}, ["appointment_id"]
            ),
        ),
        ToolSpec(
            name="qualify_lead",
            description="Registra a qualificação do lead (intenção/prioridade).",
            parameters=_obj(
                {
                    "intent": intent_prop,
                    "priority": {"type": "string", "enum": priorities},
                    "notes": _str("observações (opcional)"),
                },
                ["intent", "priority"],
            ),
        ),
        ToolSpec(
            name="escalate_to_human",
            description="Transfere a conversa para um atendente humano.",
            parameters=_obj(
                {
                    "reason": {"type": "string", "enum": reasons},
                    "routing_hint": _str("para quem direcionar (opcional)"),
                },
                ["reason"],
            ),
        ),
    ]
