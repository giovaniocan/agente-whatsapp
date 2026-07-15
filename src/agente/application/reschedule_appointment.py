"""Use case: reagendar — valida o novo horário (RN-13) e recria lembretes (RN-50)."""

from datetime import datetime
from zoneinfo import ZoneInfo

from agente.application.errors import InvalidIntentError, SlotTakenError
from agente.application.reminders import schedule_reminders
from agente.domain.crm import Appointment
from agente.domain.ports import CRMPort, SchedulerPort
from agente.domain.scheduling import available_slots, is_slot_available
from agente.domain.tenant import Tenant

_MAX_ALTERNATIVES = 5


class RescheduleAppointment:
    def __init__(self, tenant: Tenant, crm: CRMPort, scheduler: SchedulerPort) -> None:
        self._tenant = tenant
        self._crm = crm
        self._scheduler = scheduler

    async def execute(
        self,
        appointment_id: str,
        new_start: datetime,
        phone: str,
        now: datetime,
    ) -> Appointment:
        current = await self._crm.get_appointment(appointment_id)
        if current is None:
            raise KeyError(f"agendamento inexistente: {appointment_id}")

        service = self._tenant.service_for(current.intent)
        if service is None:
            raise InvalidIntentError(current.intent, self._tenant.intents)

        tz = ZoneInfo(self._tenant.scheduling.timezone)
        day = new_start.astimezone(tz).date()
        # o próprio agendamento não pode bloquear a si mesmo ao mudar de horário.
        busy = [
            a for a in await self._crm.get_scheduled_appointments(day) if a.id != appointment_id
        ]

        if not is_slot_available(self._tenant.scheduling, service, new_start, busy, now=now):
            alternatives = available_slots(
                self._tenant.scheduling, service, day, busy, now=now
            )[:_MAX_ALTERNATIVES]
            raise SlotTakenError([s.start.isoformat() for s in alternatives])

        moved = await self._crm.reschedule_appointment(appointment_id, new_start)

        # RN-50: lembretes antigos fora, novos no lugar.
        await self._scheduler.cancel_by_correlation(appointment_id)
        await schedule_reminders(self._scheduler, self._tenant, moved, phone)
        return moved
