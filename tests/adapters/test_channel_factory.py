"""Fábrica de canal: channel.type → adapter (RN-40b)."""

import pytest

from agente.adapters.whatsapp.factory import build_channel
from agente.adapters.whatsapp.zapi import ZapiWhatsApp
from agente.domain.tenant import ChannelConfig


def test_zapi_type_returns_zapi_adapter() -> None:
    assert isinstance(build_channel(ChannelConfig(type="zapi")), ZapiWhatsApp)


def test_evolution_is_not_implemented_yet() -> None:
    with pytest.raises(NotImplementedError, match="06"):
        build_channel(ChannelConfig(type="evolution"))


def test_unknown_type_raises_value_error() -> None:
    with pytest.raises(ValueError, match="zapi"):
        build_channel(ChannelConfig(type="telegram"))
