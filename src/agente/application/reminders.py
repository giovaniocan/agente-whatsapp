"""Lógica de lembretes (RN-50), compartilhada por agendar e reagendar."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from agente.domain.crm import Appointment
from agente.domain.ports import SchedulerPort
from agente.domain.tenant import Tenant


def reminder_run_ats(tenant: Tenant, appointment: Appointment) -> list[datetime]:
    # Véspera, manhã do dia (09:00 local) e 1h antes — no fuso do tenant.
    tz = ZoneInfo(tenant.scheduling.timezone)
    local_day = appointment.start.astimezone(tz).date()
    return [
        appointment.start - timedelta(days=1),
        datetime.combine(local_day, time(9, 0), tzinfo=tz),
        appointment.start - timedelta(hours=1),
    ]


async def schedule_reminders(
    scheduler: SchedulerPort, tenant: Tenant, appointment: Appointment, phone: str
) -> None:
    payload = {
        "appointment_id": appointment.id,
        "phone": phone,
        "tenant_id": tenant.id,
        "start": appointment.start.isoformat(),   # o handler monta a mensagem disto
    }
    for run_at in reminder_run_ats(tenant, appointment):
        await scheduler.schedule(
            "reminder", run_at, payload, correlation_id=appointment.id
        )
