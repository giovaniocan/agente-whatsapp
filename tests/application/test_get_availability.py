"""Use case GetAvailability — slots do serviço no dia (Plano 04.3)."""

from collections.abc import Callable
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from agente.adapters.crm.fake_crm import FakeCRM
from agente.application.errors import InvalidIntentError
from agente.application.get_availability import GetAvailability
from agente.domain.tenant import Tenant

SP = ZoneInfo("America/Sao_Paulo")
MONDAY = date(2026, 7, 20)


async def test_lists_free_slots_for_intent(make_tenant: Callable[..., Tenant]) -> None:
    crm = FakeCRM()
    use_case = GetAvailability(make_tenant(), crm)
    now = datetime(2026, 7, 20, 8, 0, tzinfo=SP)

    slots = await use_case.execute(intent="haircut", day=MONDAY, now=now)

    assert slots
    assert all(s.start.tzinfo is not None for s in slots)


async def test_unknown_intent_is_rejected(make_tenant: Callable[..., Tenant]) -> None:
    use_case = GetAvailability(make_tenant(), FakeCRM())
    now = datetime(2026, 7, 20, 8, 0, tzinfo=SP)

    with pytest.raises(InvalidIntentError):
        await use_case.execute(intent="buy_vehicle", day=MONDAY, now=now)
