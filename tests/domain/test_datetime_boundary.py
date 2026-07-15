"""RN-14: o domínio recusa datetime naïve (sem fuso) na fronteira de agenda."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from agente.domain.crm import AppointmentRequest, AvailableSlot

SP = ZoneInfo("America/Sao_Paulo")


def test_available_slot_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError):
        AvailableSlot(
            start=datetime(2026, 7, 20, 10, 0),  # naïve, sem tzinfo
            end=datetime(2026, 7, 20, 11, 0),
        )


def test_available_slot_accepts_aware_datetime() -> None:
    slot = AvailableSlot(
        start=datetime(2026, 7, 20, 10, 0, tzinfo=SP),
        end=datetime(2026, 7, 20, 11, 0, tzinfo=SP),
    )
    assert slot.start.tzinfo is not None


def test_appointment_request_rejects_naive_start() -> None:
    with pytest.raises(ValidationError):
        AppointmentRequest(
            contact_id="c1",
            intent="buy_vehicle",
            start=datetime(2026, 7, 20, 10, 0),  # naïve
        )
