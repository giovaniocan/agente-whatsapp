"""Testes da ficha do tenant — foco nas regras RN-02 e RN-11."""

from collections.abc import Callable

import pytest
from pydantic import ValidationError

from agente.domain.tenant import Service, Tenant


def test_service_intent_must_be_declared_in_tenant(
    make_tenant: Callable[..., Tenant],
) -> None:
    # RN-02: um serviço só pode apontar para uma intent declarada na ficha.
    with pytest.raises(ValidationError):
        make_tenant(
            intents=["buy_vehicle"],
            services=[Service(name="Alugar", intent="rent_vehicle", duration_minutes=60)],
        )


def test_declared_intents_are_accepted(make_tenant: Callable[..., Tenant]) -> None:
    tenant = make_tenant(
        intents=["buy_vehicle", "sell_vehicle"],
        services=[
            Service(name="Comprar", intent="buy_vehicle", duration_minutes=60),
            Service(name="Vender", intent="sell_vehicle", duration_minutes=60),
        ],
    )
    assert {s.intent for s in tenant.services} == {"buy_vehicle", "sell_vehicle"}


def test_service_capacity_defaults_to_one() -> None:
    # RN-11: sem declarar, capacidade é 1 (um atendimento por vez).
    assert Service(name="Corte", intent="haircut", duration_minutes=45).capacity == 1


def test_service_capacity_is_configurable() -> None:
    # Revenda: 3 simultâneos; salão: 2 cabeleireiras, 1 manicure.
    corte = Service(name="Corte", intent="haircut", duration_minutes=45, capacity=2)
    unha = Service(name="Unha", intent="nails", duration_minutes=60, capacity=1)
    assert (corte.capacity, unha.capacity) == (2, 1)


def test_service_for_returns_service_of_intent(make_tenant: Callable[..., Tenant]) -> None:
    tenant = make_tenant(
        intents=["buy_vehicle", "sell_vehicle"],
        services=[
            Service(name="Comprar", intent="buy_vehicle", duration_minutes=60, capacity=3),
            Service(name="Vender", intent="sell_vehicle", duration_minutes=60, capacity=3),
        ],
    )
    assert tenant.service_for("sell_vehicle").name == "Vender"
    assert tenant.service_for("rent_vehicle") is None
