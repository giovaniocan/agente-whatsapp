"""Fixtures da camada de API: um tenant de salão pronto."""

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
            ],
            "scheduling": SchedulingPolicy(
                working_hours=[WorkingHours(weekday=0, open="09:00", close="18:00")],
            ),
            "crm": CRMConfig(type="fake"),
        }
        data.update(overrides)
        return Tenant(**data)

    return _make
