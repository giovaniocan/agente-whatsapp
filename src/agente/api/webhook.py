"""
Webhook do WhatsApp (RN-40/41/42/45).

Responde 200 IMEDIATO e joga o processamento para background (gateways têm
timeout). Identifica o tenant pelo token do path, filtra (parser), deduplica
(RN-42) e enfileira. O "processador" é injetado — vira o buffer de debounce
(6.4) + o maestro (ProcessIncomingMessage).
"""

from collections.abc import Awaitable, Callable

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import JSONResponse

from agente.adapters.whatsapp.incoming import parse_incoming
from agente.adapters.whatsapp.zapi_parser import Ignored
from agente.domain.messaging import IncomingMessage
from agente.domain.ports import ConversationStorePort
from agente.domain.tenant import Tenant

Processor = Callable[[Tenant, IncomingMessage], Awaitable[None]]


def create_app(
    registry: dict[str, Tenant],
    store: ConversationStorePort,
    processor: Processor,
) -> FastAPI:
    app = FastAPI(title="Agente WhatsApp")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/webhook/whatsapp/{token}")
    async def webhook(
        token: str, request: Request, background: BackgroundTasks
    ) -> JSONResponse:
        tenant = registry.get(token)
        if tenant is None:
            return JSONResponse({"ok": False, "reason": "unauthorized"}, status_code=401)

        payload = await request.json()
        parsed = parse_incoming(tenant.channel.type, payload)
        if isinstance(parsed, Ignored):
            return JSONResponse({"ok": True, "skipped": parsed.reason})

        # RN-42: reentrega do webhook não processa duas vezes.
        if await store.mark_message_seen(parsed.message_id):
            return JSONResponse({"ok": True, "skipped": "duplicate"})

        # RN-45: 200 imediato; processamento em background.
        background.add_task(processor, tenant, parsed)
        return JSONResponse({"ok": True})

    return app
