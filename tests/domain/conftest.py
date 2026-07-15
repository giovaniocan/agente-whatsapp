"""Fixtures compartilhadas dos testes de domínio."""

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
    """Fábrica de Tenant mínimo válido; o teste sobrescreve o que precisar."""

    def _make(**overrides: Any) -> Tenant:
        data: dict[str, Any] = {
            "id": "t1",
            "name": "Tenant de Teste",
            "persona": Persona(name="Ana", tone="cordial"),
            "intents": ["buy_vehicle", "sell_vehicle"],
            "services": [
                Service(name="Comprar veículo", intent="buy_vehicle", duration_minutes=60),
            ],
            "scheduling": SchedulingPolicy(
                working_hours=[WorkingHours(weekday=0, open="09:00", close="18:00")],
            ),
            "crm": CRMConfig(type="fake"),
        }
        data.update(overrides)
        return Tenant(**data)

    return _make
