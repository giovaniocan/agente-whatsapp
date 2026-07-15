"""
Catálogo de ferramentas oferecidas ao LLM.

Fronteira humana POR DESIGN (RN-30): a lista de ferramentas permitidas NUNCA
inclui preço, desconto, negociação, financiamento ou fechamento de contrato.
O modelo não pode fazer o que não tem ferramenta para fazer.

Aqui os ToolSpec são mínimos (nome + descrição). O plano 07 os enriquece com o
JSON Schema completo e as intents da ficha.
"""

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

_DESCRIPTIONS = {
    "get_availability": "Lista horários livres para um serviço num dia.",
    "schedule_appointment": "Agenda um atendimento em um horário livre.",
    "reschedule_appointment": "Move um agendamento para outro horário.",
    "cancel_appointment": "Cancela um agendamento.",
    "qualify_lead": "Registra a qualificação do lead (intenção/prioridade).",
    "escalate_to_human": "Transfere a conversa para um atendente humano.",
}


def build_tool_specs(tenant: Tenant) -> list[ToolSpec]:
    return [
        ToolSpec(name=name, description=_DESCRIPTIONS[name]) for name in ALLOWED_TOOLS
    ]
