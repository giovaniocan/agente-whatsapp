"""
LeadInfo = o lead "em construção" durante a conversa (entidade de runtime).

Não confundir com `Contact` (domain/crm.py): Contact é o que já está GRAVADO
no CRM; LeadInfo é o rascunho que o cérebro vai preenchendo enquanto fala com
a pessoa. Por isso a maioria dos campos é opcional — no começo da conversa
sabemos pouco.
"""

from pydantic import BaseModel

from agente.domain.enums import LeadPriority


class LeadInfo(BaseModel):
    # Mínimo para o lead existir:
    full_name: str
    phone: str
    intent: str                                 # RN-02: intent do vocabulário do tenant

    # Enriquecido ao longo da conversa:
    priority: LeadPriority = LeadPriority.MEDIUM
    source: str | None = None                   # de onde veio (marketing/origem)
    vehicle_model: str | None = None
    vehicle_color: str | None = None
    email: str | None = None
    notes: str | None = None
