"""Decoradores de canal (Plano 11): shadow mode e gravação de histórico."""

from agente.adapters.store.fake_store import FakeConversationStore
from agente.adapters.whatsapp.decorators import RecordingChannel, ShadowChannel
from agente.adapters.whatsapp.fake_whatsapp import FakeWhatsApp


async def test_shadow_channel_redirects_to_team() -> None:
    # 11.5: em shadow a IA só SUGERE — cliente nunca recebe.
    inner = FakeWhatsApp()
    shadow = ShadowChannel(inner, team_phone="5511999990000")

    await shadow.send_text("44999998888", "Agendado para às 11h!")

    assert len(inner.sent) == 1
    phone, text = inner.sent[0]
    assert phone == "5511999990000"                 # foi para o time
    assert "44999998888" in text                    # identifica o cliente
    assert "Agendado para às 11h!" in text


async def test_recording_channel_stores_outgoing_message() -> None:
    inner = FakeWhatsApp()
    store = FakeConversationStore()
    channel = RecordingChannel(inner, store, tenant_id="salao")

    await channel.send_text("44999998888", "Olá!")

    assert inner.sent == [("44999998888", "Olá!")]  # envio passa adiante
    history = await store.recent_messages("salao", "44999998888", limit=5)
    assert [(m.direction, m.text) for m in history] == [("out", "Olá!")]
