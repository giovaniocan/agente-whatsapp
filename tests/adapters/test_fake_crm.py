"""FakeCRM em memória cumprindo a CRMPort (Plano 03)."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from agente.adapters.crm.fake_crm import FakeCRM
from agente.domain.crm import AppointmentRequest, HandoffTask
from agente.domain.enums import EscalationTrigger, LeadPriority
from agente.domain.ports import CRMPort

SP = ZoneInfo("America/Sao_Paulo")
DAY = date(2026, 7, 20)


def _start(hour: int) -> datetime:
    return datetime(DAY.year, DAY.month, DAY.day, hour, 0, tzinfo=SP)


def test_fake_crm_satisfies_the_port() -> None:
    assert isinstance(FakeCRM(), CRMPort)


async def test_create_and_find_contact() -> None:
    crm = FakeCRM()
    created = await crm.create_contact("João Silva", "44999998888")

    assert created.id
    found = await crm.find_contact_by_phone("44999998888")
    assert found is not None and found.id == created.id


async def test_find_unknown_phone_returns_none() -> None:
    assert await FakeCRM().find_contact_by_phone("11888887777") is None


async def test_find_contact_by_ninth_digit_variant() -> None:
    # RN-22: salvo com 11 dígitos, achado buscando com 10.
    crm = FakeCRM()
    await crm.create_contact("Maria", "44999998888")
    assert await crm.find_contact_by_phone("4499998888") is not None


async def test_create_appointment_shows_in_agenda() -> None:
    crm = FakeCRM()
    contact = await crm.create_contact("João", "44999998888")
    appt = await crm.create_appointment(
        AppointmentRequest(
            contact_id=contact.id, intent="buy_vehicle", start=_start(10), end=_start(11)
        )
    )
    agenda = await crm.get_scheduled_appointments(DAY)
    assert [a.id for a in agenda] == [appt.id]


async def test_cancel_and_reschedule() -> None:
    crm = FakeCRM()
    contact = await crm.create_contact("João", "44999998888")
    appt = await crm.create_appointment(
        AppointmentRequest(
            contact_id=contact.id, intent="buy_vehicle", start=_start(10), end=_start(11)
        )
    )

    moved = await crm.reschedule_appointment(appt.id, _start(14))
    assert moved.start == _start(14)
    assert moved.end == _start(14) + timedelta(hours=1)   # mantém a duração

    await crm.cancel_appointment(appt.id)
    assert await crm.get_scheduled_appointments(DAY) == []


async def test_qualification_and_handoff_are_recorded() -> None:
    crm = FakeCRM()
    contact = await crm.create_contact("João", "44999998888")

    await crm.update_lead_qualification(
        contact.id, intent="buy_vehicle", priority=LeadPriority.HIGH, notes="urgente"
    )
    updated = await crm.find_contact_by_phone("44999998888")
    assert updated is not None and updated.intent == "buy_vehicle"
    assert updated.priority is LeadPriority.HIGH

    await crm.create_handoff_task(
        HandoffTask(
            contact_id=contact.id,
            reason=EscalationTrigger.EXPLICIT_REQUEST,
            priority=LeadPriority.HIGH,
            context="cliente pediu humano",
        )
    )
    assert len(crm.handoff_tasks) == 1


async def test_cancel_unknown_appointment_raises() -> None:
    with pytest.raises(KeyError):
        await FakeCRM().cancel_appointment("nope")
