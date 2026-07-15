"""
ZapiWhatsApp — envia mensagens via Z-API (implementa WhatsAppPort).

Endpoint: POST {base_url}/instances/{instance}/token/{token}/send-text
Header opcional Client-Token (segurança de conta). Retry com backoff em 5xx.
Toda I/O é async (RN-65).
"""

import asyncio

import httpx

from agente.domain.tenant import ChannelConfig


class ZapiWhatsApp:
    def __init__(self, config: ChannelConfig, max_retries: int = 3) -> None:
        self._config = config
        self._max_retries = max_retries
        instance = config.settings.get("instance_id", "")
        self._url = f"{config.base_url}/instances/{instance}/token/{config.api_key}/send-text"
        self._client_token = config.settings.get("client_token")

    async def send_text(self, phone: str, text: str) -> None:
        headers = {}
        if self._client_token:
            headers["Client-Token"] = self._client_token
        payload = {"phone": phone, "message": text}

        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=15.0) as client:
            for attempt in range(self._max_retries):
                try:
                    response = await client.post(self._url, json=payload, headers=headers)
                    if response.status_code < 500:
                        response.raise_for_status()
                        return
                    last_error = httpx.HTTPStatusError(
                        "5xx do Z-API", request=response.request, response=response
                    )
                except httpx.HTTPError as exc:
                    last_error = exc
                await asyncio.sleep(0.2 * (attempt + 1))   # backoff simples

        raise RuntimeError(
            f"falha ao enviar via Z-API após {self._max_retries} tentativas: {last_error}"
        )
