"""
Parser do payload Z-API (RN-40/41).

Campos de identidade (phone, chatLid/senderLid, isGroup, fromMe, isNewsletter,
chatName) espelham o webhook real do Trivus (lib/zapiLeadUtils.js). Os campos de
texto (`text.message`) e `messageId` seguem o formato documentado do Z-API —
CONFIRMAR contra um payload real da instância antes do go-live (nota do Plano 06).
"""

from agente.adapters.whatsapp.zapi_parser import Ignored, parse_zapi
from agente.domain.messaging import IncomingMessage


def _text_payload(**over: object) -> dict:
    data: dict[str, object] = {
        "phone": "5544999998888",
        "chatName": "Maria",
        "messageId": "MSG-1",
        "text": {"message": "quero agendar"},
    }
    data.update(over)
    return data


def test_text_message_is_parsed_and_phone_normalized() -> None:
    result = parse_zapi(_text_payload())
    assert isinstance(result, IncomingMessage)
    assert result.phone == "44999998888"      # DDI 55 removido
    assert result.text == "quero agendar"
    assert result.message_id == "MSG-1"


def test_group_is_ignored() -> None:
    result = parse_zapi(_text_payload(isGroup=True))
    assert isinstance(result, Ignored) and result.reason == "group"


def test_from_me_is_ignored() -> None:
    result = parse_zapi(_text_payload(fromMe=True))
    assert isinstance(result, Ignored) and result.reason == "from_me"


def test_newsletter_is_ignored() -> None:
    result = parse_zapi(_text_payload(isNewsletter=True))
    assert isinstance(result, Ignored) and result.reason == "newsletter"


def test_lid_only_contact_keeps_lid_without_phone() -> None:
    result = parse_zapi(
        _text_payload(phone="63312750448861@lid", chatLid="63312750448861@lid")
    )
    assert isinstance(result, IncomingMessage)
    assert result.phone is None
    assert result.lid == "63312750448861"


def test_message_without_identity_is_ignored() -> None:
    result = parse_zapi({"messageId": "X", "text": {"message": "oi"}})
    assert isinstance(result, Ignored) and result.reason == "no_identity"


def test_message_without_text_is_ignored() -> None:
    result = parse_zapi(_text_payload(text={}))
    assert isinstance(result, Ignored) and result.reason == "no_text"
