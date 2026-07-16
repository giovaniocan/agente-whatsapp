"""Fábrica de CRM: resolve CRMConfig.type → adapter (RN-03)."""

import pytest

from agente.adapters.crm.factory import build_crm
from agente.adapters.crm.fake_crm import FakeCRM
from agente.domain.tenant import CRMConfig


def test_fake_type_returns_fake_crm() -> None:
    assert isinstance(build_crm(CRMConfig(type="fake")), FakeCRM)


def test_trivus_type_returns_trivus_adapter() -> None:
    from agente.adapters.crm.trivus import TrivusCRM

    assert isinstance(build_crm(CRMConfig(type="trivus", api_key="x")), TrivusCRM)


def test_unknown_type_raises_value_error_listing_valid() -> None:
    with pytest.raises(ValueError, match="fake"):
        build_crm(CRMConfig(type="banana"))


async def test_instances_are_isolated() -> None:
    # RN-03: cada tenant tem seu adapter; um não enxerga dados do outro.
    a = build_crm(CRMConfig(type="fake"))
    b = build_crm(CRMConfig(type="fake"))
    await a.create_contact("João", "44999998888")
    assert await b.find_contact_by_phone("44999998888") is None
