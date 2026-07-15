"""
Parser do payload Z-API → IncomingMessage neutro (RN-40/41).

Regras de identidade portadas do webhook real do Trivus (zapiLeadUtils.js):
o `phone` pode trazer o número real ("55DD9...@c.us") ou um lid ("...@lid"),
que NÃO é telefone. Filtramos grupo/fromMe/newsletter antes de tudo.
"""

from dataclasses import dataclass

from agente.domain.messaging import IncomingMessage
from agente.utils.phone import only_digits


@dataclass(frozen=True)
class Ignored:
    reason: str


def _extract_identity(payload: dict[str, object]) -> tuple[str | None, str | None]:
    phone_field = str(payload.get("phone") or "")
    is_lid_phone = "@lid" in phone_field

    lid_source = str(
        payload.get("chatLid") or payload.get("senderLid") or (phone_field if is_lid_phone else "")
    )
    lid = only_digits(lid_source.split("@")[0]) or None

    phone: str | None = None
    if not is_lid_phone:
        digits = only_digits(phone_field.split("@")[0])
        # remove DDI 55 (Brasil): 12-13 dígitos → 10-11.
        if len(digits) in (12, 13) and digits.startswith("55"):
            digits = digits[2:]
        phone = digits or None

    return phone, lid


def parse_zapi(payload: dict[str, object]) -> IncomingMessage | Ignored:
    if payload.get("isGroup"):
        return Ignored("group")
    if payload.get("fromMe"):
        return Ignored("from_me")
    if payload.get("isNewsletter"):
        return Ignored("newsletter")

    text = ""
    raw_text = payload.get("text")
    if isinstance(raw_text, dict):
        text = str(raw_text.get("message") or "").strip()
    if not text:
        return Ignored("no_text")

    phone, lid = _extract_identity(payload)
    if not phone and not lid:
        return Ignored("no_identity")

    sender = str(payload.get("chatName") or payload.get("senderName") or "") or None
    return IncomingMessage(
        text=text,
        message_id=str(payload.get("messageId") or ""),
        phone=phone,
        lid=lid,
        sender_name=sender,
    )
