"""Testes do LeadInfo — RN-02 (intent agnóstica a ramo)."""

from agente.domain.enums import LeadPriority
from agente.domain.lead import LeadInfo


def test_lead_intent_is_a_free_string_not_a_fixed_enum() -> None:
    # RN-02: o motor não conhece "buy/sell"; a intent vem do vocabulário do tenant.
    # Um salão usa "haircut" — tem que ser aceito sem enum fixo.
    lead = LeadInfo(full_name="Maria Souza", phone="44999998888", intent="haircut")
    assert lead.intent == "haircut"
    assert lead.priority is LeadPriority.MEDIUM
