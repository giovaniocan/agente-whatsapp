"""FakeWhatsApp — WhatsAppPort em memória (guarda o que foi enviado)."""


class FakeWhatsApp:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_text(self, phone: str, text: str) -> None:
        self.sent.append((phone, text))
