"""
Use case: agendar um atendimento.

Reúne três regras: valida dados obrigatórios (RN-20), revalida o horário no
COMMIT contra a corrida de duas conversas (RN-13) e agenda os 3 lembretes
(RN-50). Nada de sobrescrever: se o horário lotou, oferece alternativas.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from agente.application.errors import (
    InvalidIntentError,
    MissingLeadDataError,
    SlotTakenError,
)
from agente.application.reminders import schedule_reminders
from agente.domain.crm import Appointment, AppointmentRequest
from agente.domain.lead import LeadInfo
from agente.domain.ports import CRMPort, SchedulerPort
from agente.domain.scheduling import available_slots, is_slot_available
from agente.domain.tenant import Tenant

_MAX_ALTERNATIVES = 5


class ScheduleAppointment:
    def __init__(self, tenant: Tenant, crm: CRMPort, scheduler: SchedulerPort) -> None:
        self._tenant = tenant
        self._crm = crm
        self._scheduler = scheduler

    async def execute(
        self,
        draft: LeadInfo | None,
        contact_id: str,
        start: datetime | None,
        now: datetime,
    ) -> Appointment:
        missing = self._missing_fields(draft, start)
        if missing:
            raise MissingLeadDataError(missing)
        assert draft is not None and start is not None  # garantido acima

        service = self._tenant.service_for(draft.intent)
        if service is None:
            raise InvalidIntentError(draft.intent, self._tenant.intents)

        tz = ZoneInfo(self._tenant.scheduling.timezone)
        day = start.astimezone(tz).date()
        busy = await self._crm.get_scheduled_appointments(day)

        # RN-13: revalida no momento do commit.
        if not is_slot_available(self._tenant.scheduling, service, start, busy, now=now):
            alternatives = available_slots(
                self._tenant.scheduling, service, day, busy, now=now
            )[:_MAX_ALTERNATIVES]
            raise SlotTakenError([s.start.isoformat() for s in alternatives])

        end = start + timedelta(minutes=service.duration_minutes)
        appointment = await self._crm.create_appointment(
            AppointmentRequest(
                contact_id=contact_id,
                intent=draft.intent,
                start=start,
                end=end,
                notes=draft.notes,
            )
        )
        await schedule_reminders(self._scheduler, self._tenant, appointment, draft.phone)
        return appointment

    def _missing_fields(self, draft: LeadInfo | None, start: datetime | None) -> list[str]:
        missing: list[str] = []
        if draft is None or not draft.full_name.strip():
            missing.append("full_name")
        if draft is None or not draft.intent.strip():
            missing.append("intent")
        if start is None:
            missing.append("appointment_time")
        return missing
