"""
Bootstrap — a raiz de composição de PRODUÇÃO (Plano 11).

Lê as fichas de `tenants_dir`, monta os adapters de cada tenant pelas fábricas
(CRM/canal/LLM), liga pipeline → debounce → webhook e expõe o app FastAPI e as
peças que o worker usa. Tenant cujo adapter ainda não existe (ex.: crm "trivus"
até o Plano 08) é PULADO com warning — o boot nunca cai por causa de um tenant.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agente.adapters.crm.factory import build_crm
from agente.adapters.llm.factory import build_llm
from agente.adapters.scheduler.postgres_scheduler import JobWorker, PostgresScheduler
from agente.adapters.store.postgres_store import PostgresConversationStore
from agente.adapters.vectorstore.embedder import FakeEmbedder, OpenAIEmbedder
from agente.adapters.vectorstore.pgvector_store import PgVectorKnowledgeStore
from agente.adapters.whatsapp.decorators import ShadowChannel
from agente.adapters.whatsapp.factory import build_channel
from agente.api.webhook import create_app
from agente.application.debounce import DebounceBuffer
from agente.application.job_handlers import build_job_handlers
from agente.application.pipeline import MessagePipeline
from agente.config.settings import Settings
from agente.config.tenant_loader import TenantConfigError, load_tenant_file
from agente.domain.ports import EmbeddingPort, WhatsAppPort
from agente.domain.tenant import Tenant

logger = logging.getLogger(__name__)


@dataclass
class Runtime:
    app: FastAPI
    registry_by_token: dict[str, Tenant]
    registry_by_id: dict[str, Tenant]
    sessionmaker: async_sessionmaker[AsyncSession]
    store: PostgresConversationStore
    scheduler: PostgresScheduler
    pipelines: dict[str, MessagePipeline] = field(default_factory=dict)

    def build_worker(self) -> JobWorker:
        handlers = build_job_handlers(
            self.registry_by_id, self.store, self._outbound_channel
        )
        return JobWorker(self.sessionmaker, handlers)

    def _outbound_channel(self, tenant: Tenant) -> WhatsAppPort:
        channel: WhatsAppPort = build_channel(tenant.channel)
        if tenant.mode == "shadow":               # lembretes também não vazam (11.5)
            channel = ShadowChannel(channel, tenant.handoff.team_phone)
        return channel


def build_embedder() -> EmbeddingPort:
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIEmbedder(api_key=os.environ["OPENAI_API_KEY"])
    logger.warning("OPENAI_API_KEY ausente — FakeEmbedder (RAG só p/ dev/demo)")
    return FakeEmbedder()


def build_runtime(settings: Settings) -> Runtime:
    engine = create_async_engine(settings.database_url)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    store = PostgresConversationStore(sessionmaker)
    scheduler = PostgresScheduler(sessionmaker)
    knowledge = PgVectorKnowledgeStore(sessionmaker, build_embedder())

    registry_by_token: dict[str, Tenant] = {}
    registry_by_id: dict[str, Tenant] = {}
    pipelines: dict[str, MessagePipeline] = {}

    tenants_dir = Path(settings.tenants_dir)
    for path in sorted(tenants_dir.glob("*.json")):
        try:
            tenant = load_tenant_file(path)
            pipelines[tenant.id] = MessagePipeline(
                tenant=tenant,
                store=store,
                crm=build_crm(tenant.crm),
                scheduler=scheduler,
                llm=build_llm(tenant.llm),
                channel=build_channel(tenant.channel),
                knowledge=knowledge,
            )
        except (TenantConfigError, NotImplementedError, ValueError) as exc:
            logger.warning("tenant %s pulado no boot: %s", path.name, exc)
            continue
        registry_by_id[tenant.id] = tenant
        if tenant.webhook_token:
            registry_by_token[tenant.webhook_token] = tenant
        else:
            logger.warning("tenant %s sem webhook_token — inacessível via webhook", tenant.id)

    async def downstream(tenant: Tenant, phone: str, text: str) -> None:
        await pipelines[tenant.id].handle(phone, text)

    debounce = DebounceBuffer(downstream, store, window=settings.debounce_seconds)

    app = create_app(
        registry_by_token,
        store,
        processor=debounce,
        rate_limit_per_minute=settings.webhook_rate_limit_per_minute,
    )

    return Runtime(
        app=app,
        registry_by_token=registry_by_token,
        registry_by_id=registry_by_id,
        sessionmaker=sessionmaker,
        store=store,
        scheduler=scheduler,
        pipelines=pipelines,
    )
