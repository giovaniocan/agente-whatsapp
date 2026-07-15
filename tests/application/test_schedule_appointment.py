"""Use case ScheduleAppointment — RN-13 (recheck), RN-20 (dados), RN-50 (lembretes)."""

from collections.abc import Callable
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from agente.adapters.crm.fake_crm import FakeCRM
from agente.adapters.scheduler.fake_scheduler import FakeScheduler
from agente.application.errors import MissingLeadDataError, SlotTakenError
from agente.application.schedule_appointment import ScheduleAppointment
from agente.domain.crm import AppointmentRequest
from agente.domain.lead import LeadInfo
from agente.domain.tenant import Tenant

SP = ZoneInfo("America/Sao_Paulo")
MONDAY = date(2026, 7, 20)
NOW = datetime(2026, 7, 20, 8, 0, tzinfo=SP)


def _at(hour: int) -> datetime:
    return datetime(2026, 7, 20, hour, 0, tzinfo=SP)


def _draft(**over: object) -> LeadInfo:
    data: dict[str, object] = {"full_name": "Maria", "phone": "44999998888", "intent": "nails"}
    data.update(over)
    return LeadInfo(**data)  # type: ignore[arg-type]


def _use_case(tenant: Tenant, crm: FakeCRM, scheduler: FakeScheduler) -> ScheduleAppointment:
    return ScheduleAppointment(tenant, crm, scheduler)


async def test_missing_name_lists_the_field(make_tenant: Callable[..., Tenant]) -> None:
    uc = _use_case(make_tenant(), FakeCRM(), FakeScheduler())
    with pytest.raises(MissingLeadDataError) as exc:
        await uc.execute(draft=_draft(full_name=""), contact_id="c1", start=_at(11), now=NOW)
    assert "full_name" in exc.value.missing


async def test_missing_time_lists_the_field(make_tenant: Callable[..., Tenant]) -> None:
    uc = _use_case(make_tenant(), FakeCRM(), FakeScheduler())
    with pytest.raises(MissingLeadDataError) as exc:
        await uc.execute(draft=_draft(), contact_id="c1", start=None, now=NOW)
    assert "appointment_time" in exc.value.missing


async def test_slot_taken_between_offer_and_commit(
    make_tenant: Callable[..., Tenant],
) -> None:
    # RN-13: outra conversa lotou a vaga (nails capacidade 1) às 10h.
    crm = FakeCRM()
    await crm.create_appointment(
        AppointmentRequest(contact_id="other", intent="nails", start=_at(10), end=_at(11))
    )
    uc = _use_case(make_tenant(), crm, FakeScheduler())

    with pytest.raises(SlotTakenError) as exc:
        await uc.execute(draft=_draft(), contact_id="c1", start=_at(10), now=NOW)
    assert exc.value.alternatives   # oferece outros horários


async def test_valid_slot_creates_appointment_and_three_reminders(
    make_tenant: Callable[..., Tenant],
) -> None:
    crm = FakeCRM()
    scheduler = FakeScheduler()
    uc = _use_case(make_tenant(), crm, scheduler)

    appt = await uc.execute(draft=_draft(), contact_id="c1", start=_at(11), now=NOW)

    # agendamento criado com a duração do serviço (nails = 60min)
    assert appt.end == _at(12)
    assert appt.id in {a.id for a in await crm.get_scheduled_appointments(MONDAY)}

    # RN-50: 3 lembretes (véspera, manhã 09:00 do dia, 1h antes)
    run_ats = sorted(j.run_at for j in scheduler.jobs.values())
    assert len(run_ats) == 3
    assert run_ats == [
        _at(11) - timedelta(days=1),                          # véspera
        datetime(2026, 7, 20, 9, 0, tzinfo=SP),               # manhã do dia
        _at(10),                                              # 1h antes
    ]
