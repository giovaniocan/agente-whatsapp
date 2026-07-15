"""Fixtures da camada de aplicação: um tenant de salão pronto para uso."""

from collections.abc import Callable
from typing import Any

import pytest

from agente.domain.tenant import (
    CRMConfig,
    Persona,
    SchedulingPolicy,
    Service,
    Tenant,
    WorkingHours,
)


@pytest.fixture
def make_tenant() -> Callable[..., Tenant]:
    def _make(**overrides: Any) -> Tenant:
        data: dict[str, Any] = {
            "id": "salao",
            "name": "Salão Demo",
            "persona": Persona(name="Bia", tone="acolhedor"),
            "intents": ["haircut", "nails"],
            "services": [
                Service(name="Corte", intent="haircut", duration_minutes=45, capacity=2),
                Service(name="Unha", intent="nails", duration_minutes=60, capacity=1),
            ],
            "scheduling": SchedulingPolicy(
                min_notice_minutes=0,
                working_hours=[WorkingHours(weekday=0, open="09:00", close="18:00")],
            ),
            "crm": CRMConfig(type="fake"),
        }
        data.update(overrides)
        return Tenant(**data)

    return _make
