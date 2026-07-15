"""
Conversation = o estado de um papo com um telefone (entidade de runtime).

Guarda quem está no comando (handoff), o rascunho do lead e o momento da última
mudança. A máquina de estados de handoff segue a RN-31: ACTIVE (IA responde) →
PENDING (escalou, IA calada) → HUMAN (humano assumiu) → ACTIVE (auto-resume).
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from agente.domain.enums import HandoffStatus
from agente.domain.lead import LeadInfo


def _now() -> datetime:
    # RN-14: sempre tz-aware.
    return datetime.now(UTC)


class Conversation(BaseModel):
    tenant_id: str
    phone: str
    handoff_status: HandoffStatus = HandoffStatus.ACTIVE
    lead_draft: LeadInfo | None = None
    summary: str = ""                       # resumo do histórico (controle de custo do LLM)
    updated_at: datetime = Field(default_factory=_now)

    @property
    def can_ai_reply(self) -> bool:
        # RN-31: a IA só responde quando está no comando.
        return self.handoff_status is HandoffStatus.ACTIVE

    def request_handoff(self) -> None:
        self._transition(HandoffStatus.PENDING)

    def human_took_over(self) -> None:
        self._transition(HandoffStatus.HUMAN)

    def resume(self) -> None:
        self._transition(HandoffStatus.ACTIVE)

    def _transition(self, status: HandoffStatus) -> None:
        self.handoff_status = status
        self.updated_at = _now()
