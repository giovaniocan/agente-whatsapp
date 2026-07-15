"""
Modelos ORM (SQLAlchemy 2.0) do banco PRÓPRIO do agente.

Não é o banco do Trivus — aqui vivem as conversas, o dedupe de mensagens e os
jobs agendados. Datas sempre tz-aware (timestamptz).
"""

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ConversationRow(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("tenant_id", "phone", name="uq_conv_tenant_phone"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    phone: Mapped[str] = mapped_column(String(32), index=True)
    handoff_status: Mapped[str] = mapped_column(String(16), default="active")
    lead_draft: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str] = mapped_column(String, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MessageRow(Base):
    """Histórico de conversa (RN-74). Chaveado por (tenant, phone), como a
    Conversation do domínio — que não carrega id de banco."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    phone: Mapped[str] = mapped_column(String(32), index=True)
    direction: Mapped[str] = mapped_column(String(3))          # "in" | "out"
    text: Mapped[str] = mapped_column(String)
    provider_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ProcessedMessageRow(Base):
    """Idempotência do webhook (RN-42): guarda ids de mensagem já processados."""

    __tablename__ = "processed_messages"

    provider_message_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class KnowledgeChunkRow(Base):
    """Base de conhecimento por tenant (RAG, plano 10). `embedding` é um vetor
    pgvector sem dimensão fixa (a dimensão trava quando o provedor real for
    escolhido — aí entra também o índice ivfflat)."""

    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("tenant_id", "content_hash", name="uq_chunk_tenant_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(255), default="")
    content: Mapped[str] = mapped_column(String)
    content_hash: Mapped[str] = mapped_column(String(64))
    embedding: Mapped[list[float]] = mapped_column(Vector())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ScheduledJobRow(Base):
    """Jobs (lembretes, auto-resume, follow-up) — worker no plano 09."""

    __tablename__ = "scheduled_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(default=0)
