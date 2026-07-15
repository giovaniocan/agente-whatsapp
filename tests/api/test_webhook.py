"""Webhook do WhatsApp — RN-40/41/42/45 (Plano 06.3)."""

from collections.abc import Callable

from httpx import ASGITransport, AsyncClient

from agente.adapters.store.fake_store import FakeConversationStore
from agente.api.webhook import create_app
from agente.domain.messaging import IncomingMessage
from agente.domain.tenant import Tenant


class _RecordingProcessor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def __call__(self, tenant: Tenant, incoming: IncomingMessage) -> None:
        self.calls.append((tenant.id, incoming.text))


def _text_payload(**over: object) -> dict:
    data: dict[str, object] = {
        "phone": "5544999998888",
        "messageId": "MSG-1",
        "text": {"message": "quero agendar"},
    }
    data.update(over)
    return data


async def _client(app: object) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")  # type: ignore[arg-type]


def _app(
    make_tenant: Callable[..., Tenant], processor: object
) -> tuple[object, FakeConversationStore]:
    tenant = make_tenant(webhook_token="TKN-salao")
    store = FakeConversationStore()
    app = create_app(
        registry={tenant.webhook_token: tenant}, store=store, processor=processor
    )
    return app, store


async def test_unknown_token_returns_401(make_tenant: Callable[..., Tenant]) -> None:
    app, _ = _app(make_tenant, _RecordingProcessor())
    async with await _client(app) as client:
        resp = await client.post("/webhook/whatsapp/NOPE", json=_text_payload())
    assert resp.status_code == 401


async def test_group_message_is_skipped(make_tenant: Callable[..., Tenant]) -> None:
    proc = _RecordingProcessor()
    app, _ = _app(make_tenant, proc)
    async with await _client(app) as client:
        resp = await client.post("/webhook/whatsapp/TKN-salao", json=_text_payload(isGroup=True))
    assert resp.status_code == 200
    assert resp.json()["skipped"] == "group"
    assert proc.calls == []


async def test_valid_message_is_processed(make_tenant: Callable[..., Tenant]) -> None:
    proc = _RecordingProcessor()
    app, _ = _app(make_tenant, proc)
    async with await _client(app) as client:
        resp = await client.post("/webhook/whatsapp/TKN-salao", json=_text_payload())
    assert resp.status_code == 200
    assert proc.calls == [("salao", "quero agendar")]


async def test_duplicate_message_is_deduped(make_tenant: Callable[..., Tenant]) -> None:
    # RN-42: reentrega do webhook não processa duas vezes.
    proc = _RecordingProcessor()
    app, _ = _app(make_tenant, proc)
    async with await _client(app) as client:
        await client.post("/webhook/whatsapp/TKN-salao", json=_text_payload())
        resp2 = await client.post("/webhook/whatsapp/TKN-salao", json=_text_payload())
    assert resp2.json()["skipped"] == "duplicate"
    assert len(proc.calls) == 1
