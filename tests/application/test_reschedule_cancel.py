"""Reschedule/Cancel — validam slot (RN-13) e recalculam lembretes (RN-50)."""

from collections.abc import Callable
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from agente.adapters.crm.fake_crm import FakeCRM
from agente.adapters.scheduler.fake_scheduler import FakeScheduler
from agente.application.cancel_appointment import CancelAppointment
from agente.application.errors import SlotTakenError
from agente.application.reschedule_appointment import RescheduleAppointment
from agente.application.schedule_appointment import ScheduleAppointment
from agente.domain.crm import AppointmentRequest
from agente.domain.lead import LeadInfo
from agente.domain.tenant import Tenant

SP = ZoneInfo("America/Sao_Paulo")
MONDAY = date(2026, 7, 20)
NOW = datetime(2026, 7, 20, 8, 0, tzinfo=SP)


def _at(hour: int) -> datetime:
    return datetime(2026, 7, 20, hour, 0, tzinfo=SP)


async def _book(tenant: Tenant, crm: FakeCRM, sched: FakeScheduler, hour: int):  # type: ignore[no-untyped-def]
    draft = LeadInfo(full_name="Maria", phone="44999998888", intent="nails")
    return await ScheduleAppointment(tenant, crm, sched).execute(
        draft=draft, contact_id="c1", start=_at(hour), now=NOW
    )


async def test_reschedule_moves_and_recreates_reminders(
    make_tenant: Callable[..., Tenant],
) -> None:
    tenant, crm, sched = make_tenant(), FakeCRM(), FakeScheduler()
    appt = await _book(tenant, crm, sched, 11)
    assert len(sched.jobs) == 3   # lembretes do 11h

    moved = await RescheduleAppointment(tenant, crm, sched).execute(
        appointment_id=appt.id, new_start=_at(14), phone="44999998888", now=NOW
    )

    assert moved.start == _at(14)
    # ainda 3 lembretes, mas agora referentes às 14h (os antigos foram cancelados)
    assert len(sched.jobs) == 3
    assert _at(13) in {j.run_at for j in sched.jobs.values()}   # 1h antes das 14h
    assert _at(10) not in {j.run_at for j in sched.jobs.values()}  # antigo (11h-1) sumiu


async def test_reschedule_to_taken_slot_is_rejected(
    make_tenant: Callable[..., Tenant],
) -> None:
    tenant, crm, sched = make_tenant(), FakeCRM(), FakeScheduler()
    appt = await _book(tenant, crm, sched, 11)
    # outra conversa ocupa as 14h (nails capacidade 1)
    await crm.create_appointment(
        AppointmentRequest(contact_id="other", intent="nails", start=_at(14), end=_at(15))
    )

    with pytest.raises(SlotTakenError):
        await RescheduleAppointment(tenant, crm, sched).execute(
            appointment_id=appt.id, new_start=_at(14), phone="44999998888", now=NOW
        )


async def test_cancel_removes_appointment_and_reminders(
    make_tenant: Callable[..., Tenant],
) -> None:
    tenant, crm, sched = make_tenant(), FakeCRM(), FakeScheduler()
    appt = await _book(tenant, crm, sched, 11)

    await CancelAppointment(crm, sched).execute(appointment_id=appt.id)

    assert await crm.get_scheduled_appointments(MONDAY) == []
    assert sched.jobs == {}
