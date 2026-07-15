"""Use case: horários livres de um serviço num dia (RN-10/11/12)."""

from datetime import date, datetime

from agente.application.errors import InvalidIntentError
from agente.domain.crm import AvailableSlot
from agente.domain.ports import CRMPort
from agente.domain.scheduling import available_slots
from agente.domain.tenant import Tenant


class GetAvailability:
    def __init__(self, tenant: Tenant, crm: CRMPort) -> None:
        self._tenant = tenant
        self._crm = crm

    async def execute(
        self, intent: str, day: date, now: datetime
    ) -> list[AvailableSlot]:
        service = self._tenant.service_for(intent)
        if service is None:
            raise InvalidIntentError(intent, self._tenant.intents)
        busy = await self._crm.get_scheduled_appointments(day)
        return available_slots(self._tenant.scheduling, service, day, busy, now=now)
