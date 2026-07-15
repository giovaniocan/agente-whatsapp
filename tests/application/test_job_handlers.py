"""Handlers de jobs: reminder (RN-50), auto_resume (RN-31.6), follow_up (RN-51)."""

from collections.abc import Callable

from agente.adapters.store.fake_store import FakeConversationStore
from agente.adapters.whatsapp.fake_whatsapp import FakeWhatsApp
from agente.application.job_handlers import build_job_handlers
from agente.domain.tenant import Tenant


def _setup(make_tenant: Callable[..., Tenant]):  # type: ignore[no-untyped-def]
    tenant = make_tenant()
    store = FakeConversationStore()
    wpp = FakeWhatsApp()
    handlers = build_job_handlers({tenant.id: tenant}, store, lambda t: wpp)
    return tenant, store, wpp, handlers


async def test_reminder_sends_message_with_local_time(
    make_tenant: Callable[..., Tenant],
) -> None:
    tenant, store, wpp, handlers = _setup(make_tenant)

    await handlers["reminder"](
        {
            "tenant_id": tenant.id,
            "phone": "44999998888",
            "start": "2026-07-20T11:00:00-03:00",
            "appointment_id": "a1",
        }
    )

    assert len(wpp.sent) == 1
    phone, text = wpp.sent[0]
    assert phone == "44999998888"
    assert "20/07" in text and "11:00" in text     # horário local na mensagem


async def test_auto_resume_returns_control_to_ai(
    make_tenant: Callable[..., Tenant],
) -> None:
    tenant, store, wpp, handlers = _setup(make_tenant)
    conv = await store.get_or_create(tenant.id, "44999998888")
    conv.request_handoff()                          # PENDING
    await store.save(conv)

    await handlers["auto_resume"]({"tenant_id": tenant.id, "phone": "44999998888"})

    reloaded = await store.get_or_create(tenant.id, "44999998888")
    assert reloaded.can_ai_reply is True            # IA retomou


async def test_auto_resume_is_noop_when_human_took_over(
    make_tenant: Callable[..., Tenant],
) -> None:
    tenant, store, wpp, handlers = _setup(make_tenant)
    conv = await store.get_or_create(tenant.id, "44999998888")
    conv.request_handoff()
    conv.human_took_over()                          # HUMAN
    await store.save(conv)

    await handlers["auto_resume"]({"tenant_id": tenant.id, "phone": "44999998888"})

    reloaded = await store.get_or_create(tenant.id, "44999998888")
    assert reloaded.can_ai_reply is False           # humano segue no comando


async def test_follow_up_sends_only_when_ai_is_active(
    make_tenant: Callable[..., Tenant],
) -> None:
    tenant, store, wpp, handlers = _setup(make_tenant)
    payload = {"tenant_id": tenant.id, "phone": "44999998888", "message": "Ainda quer agendar?"}

    await handlers["follow_up"](payload)            # ACTIVE → envia
    assert wpp.sent == [("44999998888", "Ainda quer agendar?")]

    conv = await store.get_or_create(tenant.id, "44999998888")
    conv.request_handoff()                          # PENDING → não envia
    await store.save(conv)
    await handlers["follow_up"](payload)
    assert len(wpp.sent) == 1


async def test_unknown_tenant_raises(make_tenant: Callable[..., Tenant]) -> None:
    _, _, _, handlers = _setup(make_tenant)
    import pytest

    with pytest.raises(KeyError):
        await handlers["reminder"](
            {"tenant_id": "ghost", "phone": "1", "start": "2026-07-20T11:00:00-03:00"}
        )
