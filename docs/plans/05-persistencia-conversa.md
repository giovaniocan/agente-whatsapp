# Plano 05 — Persistência de conversa (banco do agente)

**Objetivo:** Postgres PRÓPRIO do agente (não é o banco do Trivus): conversas, mensagens,
jobs. Implementa `ConversationStorePort` e a base de locks/dedupe.
**Regras cobertas:** RN-42, RN-44, RN-63.

## Tarefa 5.1 — Infra local

- [ ] `uv add sqlalchemy[asyncio] asyncpg alembic`; `docker-compose.yml` com postgres:16
- [ ] Alembic configurado; migration 001: `conversations` (id, tenant_id, phone,
      handoff_status, lead_draft jsonb, summary text, updated_at), `messages`
      (id, conversation_id FK, direction, text, provider_message_id UNIQUE, created_at),
      `scheduled_jobs` (id, kind, run_at timestamptz, payload jsonb, status)
- [ ] Índices: `(tenant_id, phone)` UNIQUE em conversations; `run_at+status` em jobs
- [ ] Commit: `feat(infra): agent database schema (conversations, messages, jobs)`

## Tarefa 5.2 — Repositório (adapter da ConversationStorePort)

- [ ] Testes de integração (testcontainers ou compose): get_or_create por (tenant, phone);
      roundtrip de lead_draft; update de handoff_status
- [ ] Ver falhar → implementar `adapters/store/postgres_store.py`
- [ ] Teste RN-42: inserir mensagem com `provider_message_id` repetido → ignorada
      (dedupe idempotente, não exceção)
- [ ] Teste RN-44: `with lock(conversation_id)` — segunda aquisição concorrente espera
      (advisory lock do Postgres); teste com duas tasks asyncio
- [ ] Commit: `feat(adapters): postgres conversation store with dedupe and advisory locks`

## Critério de pronto

- [ ] Suíte roda com banco descartável; migrations reproduzem schema do zero
- [ ] Marcar ✅ no 00-INDEX
