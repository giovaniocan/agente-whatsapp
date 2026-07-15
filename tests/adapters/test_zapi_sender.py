"""ZapiWhatsApp.send_text — POST correto e retry (Plano 06.2), HTTP mockado."""

import json

import httpx
import pytest
import respx

from agente.adapters.whatsapp.zapi import ZapiWhatsApp
from agente.domain.ports import WhatsAppPort
from agente.domain.tenant import ChannelConfig


def _config() -> ChannelConfig:
    return ChannelConfig(
        type="zapi",
        base_url="https://api.z-api.io",
        api_key="TOKEN123",
        settings={"instance_id": "INST9", "client_token": "CT-abc"},
    )


def test_satisfies_the_port() -> None:
    assert isinstance(ZapiWhatsApp(_config()), WhatsAppPort)


@respx.mock
async def test_send_text_posts_to_zapi() -> None:
    route = respx.post(
        "https://api.z-api.io/instances/INST9/token/TOKEN123/send-text"
    ).mock(return_value=httpx.Response(200, json={"messageId": "x"}))

    await ZapiWhatsApp(_config()).send_text("44999998888", "olá!")

    assert route.called
    sent = route.calls.last.request
    assert sent.headers.get("Client-Token") == "CT-abc"
    body = json.loads(sent.content)
    assert body == {"phone": "44999998888", "message": "olá!"}


@respx.mock
async def test_send_text_retries_on_5xx_then_raises() -> None:
    route = respx.post(
        "https://api.z-api.io/instances/INST9/token/TOKEN123/send-text"
    ).mock(return_value=httpx.Response(503))

    with pytest.raises(RuntimeError):
        await ZapiWhatsApp(_config(), max_retries=3).send_text("44999998888", "oi")

    assert route.call_count == 3   # tentou 3x antes de desistir
