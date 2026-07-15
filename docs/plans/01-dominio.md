# Plano 01 — Domínio agnóstico

**Objetivo:** núcleo puro e agnóstico (RN-01/02/03): entidades, ficha do tenant, ports.
**Regras cobertas:** RN-01, RN-02, RN-03, RN-11, RN-14, RN-20, RN-66.
**Pré-existente:** `enums.py`, `tenant.py`, `lead.py`, `crm.py` (serão retocados).

## Tarefa 1.0 — Ferramentas de qualidade

- [ ] Adicionar dev-deps: `uv add --dev pytest-asyncio ruff mypy`
- [ ] Configurar `pyproject.toml`: `[tool.ruff]`, `[tool.mypy]` (strict), `asyncio_mode = "auto"`
- [ ] Rodar `uv run pytest` → deve passar (0 testes ainda) e `uv run ruff check src` limpo
- [ ] Commit: `chore: dev tooling (pytest-asyncio, ruff, mypy)`

## Tarefa 1.1 — Teste de arquitetura (guarda-costas do hexagonal)

- [ ] Escrever `tests/domain/test_architecture.py`: varre `src/agente/domain/*.py` e FALHA
      se algum arquivo importar `adapters`, `api`, `application`, `httpx`, `fastapi`,
      `sqlalchemy` ou `anthropic`
- [ ] Rodar → deve PASSAR (domínio atual é puro). Quebre de propósito (import fake) e veja
      falhar; desfaça
- [ ] Commit: `test: architecture guard for pure domain`

## Tarefa 1.2 — Retoque agnóstico: intents da ficha (RN-02)

- [ ] Teste: `Tenant` aceita `intents: list[str]` e `Service.intent` deve pertencer a elas
      (validator) — criar tenant com service de intent desconhecida → `ValidationError`
- [ ] Ver falhar → implementar em `tenant.py` (campo `intents` + `model_validator`)
- [ ] Teste: `LeadInfo.intent` vira `str` (sem enum `ServiceIntent`); remover o enum e
      atualizar imports; suíte verde
- [ ] Commit: `feat(domain): tenant-declared intents replace fixed ServiceIntent (RN-02)`

## Tarefa 1.3 — Capacidade e duração por serviço (RN-11)

- [ ] Teste: `Service` tem `capacity: int = 1` e `duration_minutes` obrigatório;
      `Tenant.service_for(intent)` devolve o serviço da intent (ou `None`)
- [ ] Ver falhar → implementar
- [ ] Teste: ficha da revenda (2 serviços 60min cap.3) e ficha de salão (corte 45min cap.2,
      unha 60min cap.1) validam — são as fixtures canônicas dos próximos planos
- [ ] Commit: `feat(domain): per-service duration and capacity (RN-11)`

## Tarefa 1.4 — Conversation (estado do atendimento)

- [ ] Teste: `Conversation` (tenant_id, phone, `handoff_status: HandoffStatus = ACTIVE`,
      `lead_draft: LeadInfo | None`, `updated_at` tz-aware) — criar/serializar roundtrip
- [ ] Ver falhar → implementar `domain/conversation.py`
- [ ] Teste: transições de handoff — `request_handoff()` → PENDING; `human_took_over()` →
      HUMAN; `resume()` → ACTIVE; IA só pode responder se `ACTIVE` (`can_ai_reply`)
- [ ] Commit: `feat(domain): Conversation entity with handoff state machine (RN-31)`

## Tarefa 1.5 — Ports (`domain/ports.py`)

- [ ] Escrever `ports.py` com `CRMPort` (8 métodos, código já revisado em aula),
      `WhatsAppPort`, `ConversationStorePort`, `SchedulerPort`, `LLMPort`, `KnowledgePort`
      — todos `Protocol`, async, tipos do domínio
- [ ] Teste: uma classe fake mínima que implementa `CRMPort` passa em
      `isinstance`-check estrutural (usar `runtime_checkable` OU teste de assinatura)
- [ ] `uv run mypy src` limpo
- [ ] Commit: `feat(domain): ports (CRMPort, WhatsAppPort, stores, scheduler, llm, knowledge)`

## Tarefa 1.6 — Datas tz-aware (RN-14)

- [ ] Teste: `AvailableSlot`/`Appointment` REJEITAM datetime naïve (validator Pydantic)
- [ ] Ver falhar → implementar validator compartilhado em `domain/crm.py`
- [ ] Commit: `feat(domain): reject naive datetimes at domain boundary (RN-14)`

## Critério de pronto do plano

- [ ] `uv run pytest` verde; `ruff` e `mypy` limpos
- [ ] Teste de arquitetura passa; nenhum vocabulário de ramo/CRM no domínio (RN-01)
- [ ] Marcar ✅ no 00-INDEX
