"""Use case: cancelar um agendamento e seus lembretes (RN-50)."""

from agente.domain.ports import CRMPort, SchedulerPort


class CancelAppointment:
    def __init__(self, crm: CRMPort, scheduler: SchedulerPort) -> None:
        self._crm = crm
        self._scheduler = scheduler

    async def execute(self, appointment_id: str) -> None:
        await self._crm.cancel_appointment(appointment_id)
        await self._scheduler.cancel_by_correlation(appointment_id)
