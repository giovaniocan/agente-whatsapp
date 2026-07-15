"""Use case: qualificar um lead (intent/prioridade/notas) no CRM (RN-21)."""

from agente.application.errors import InvalidIntentError
from agente.domain.enums import LeadPriority
from agente.domain.ports import CRMPort
from agente.domain.tenant import Tenant


class QualifyLead:
    def __init__(self, tenant: Tenant, crm: CRMPort) -> None:
        self._tenant = tenant
        self._crm = crm

    async def execute(
        self,
        contact_id: str,
        intent: str,
        priority: LeadPriority,
        notes: str | None = None,
    ) -> None:
        if intent not in self._tenant.intents:
            raise InvalidIntentError(intent, self._tenant.intents)
        await self._crm.update_lead_qualification(contact_id, intent, priority, notes)
