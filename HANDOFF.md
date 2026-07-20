# HANDOFF — Agente de IA WhatsApp (multi-tenant)

> **Documento de passagem de bastão.** Você (ou uma IA que você vai instruir)
> assume o desenvolvimento a partir daqui. Este arquivo é auto-suficiente:
> explica a ideia, a arquitetura, cada pasta, como rodar, o que está pronto, o
> que falta e **como continuar sem quebrar as decisões já tomadas**.
>
> Escrito em 16/07/2026. Estado: **9 de 11 planos concluídos; 189 testes verdes;
> ruff + mypy strict limpos.** Falta: smoke real do Trivus (Plano 08.5) e deploy
> (Plano 11) — ambos dependem de credenciais/acessos, não de código.

---

## 0. TL;DR para a IA que vai continuar

- **Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 async, Postgres+pgvector, `uv`. Testes: pytest. Lint: ruff. Tipos: mypy strict.
- **Arquitetura:** hexagonal (ports & adapters) + DDD + Anti-Corruption Layer. TDD obrigatório.
- **Fonte da verdade das regras:** [`docs/SPEC.md`](docs/SPEC.md) — regras numeradas **RN-01…RN-79**. Código e SPEC divergiram? A SPEC vence (ou corrige-se a SPEC antes).
- **Roteiro de trabalho:** [`docs/plans/00-INDEX.md`](docs/plans/00-INDEX.md) — 11 planos em baby-steps TDD. Cada plano cita as RN que cobre.
- **Antes de mexer:** `docker compose up -d` (Postgres) → `uv run pytest` (deve dar tudo verde) → `uv run ruff check src tests` → `uv run mypy src`.
- **Regra de ouro:** o motor é **agnóstico**. Nada de "veículo"/"Trivus"/"Claude" fora de `adapters/` e das fichas de tenant. Um teste de arquitetura quebra o build se o domínio importar de fora.

---

## 1. A ideia (negócio)

Um **agente de IA que atende no WhatsApp** em nome de negócios: conversa em
linguagem natural, **qualifica** o lead, **agenda** atendimentos, faz
**follow-up** e **escala para humano** quando necessário.

O princípio central é **multi-tenant**: um único motor serve vários clientes. O
que muda de um cliente para outro é uma **"ficha" (JSON de configuração)** — nunca
o código. Três eixos externos são plugáveis pela ficha:

| Eixo | O que decide | Opções hoje |
|---|---|---|
| **CRM** | onde o lead/agenda são gravados | `fake` (memória), `trivus` (trivus-api real) |
| **Canal WhatsApp** | por onde entra/sai a mensagem | `zapi` (pronto), `evolution` (encaixe pronto, não implementado) |
| **Cérebro LLM** | qual IA raciocina | `anthropic` (Claude), `openai_compat` (GPT/Groq/Ollama) |

**Clientes-alvo conhecidos:**
- **Revenda de veículos** — usa o **Trivus** (CRM próprio da holding, backend FastAPI pronto). É o 1º cliente real.
- **Clube Amore** — salões femininos (corte, unha…). Prova de que o motor é agnóstico: mesmo código, ficha diferente.
- Barbearias, clínicas etc. — qualquer negócio de "atende → qualifica → agenda".

**Fronteira humana por design:** o agente NUNCA concede desconto, negocia preço,
fecha contrato ou trata financiamento. Isso não é só instrução de prompt — essas
ferramentas **não existem** no tool-set do LLM (RN-30). Segurança por ausência.

---

## 2. Arquitetura e modelo mental

Hexagonal (ports & adapters). Dependências **sempre apontam para dentro**:

```
   WhatsApp (Z-API)          Claude / GPT           trivus-api / pgvector
        │                        │                          │
        ▼                        ▼                          ▼
┌──────────────────────── adapters/ (borda) ─────────────────────────┐
│  traduzem o mundo externo ↔ tipos limpos do domínio (o ACL)        │
└───────────────────────────────┬────────────────────────────────────┘
                                 │  usam PORTAS (interfaces)
┌───────────────────────────────▼────────────────────────────────────┐
│  application/  — casos de uso: orquestram as portas                 │
├─────────────────────────────────────────────────────────────────────┤
│  domain/       — entidades + portas + regras PURAS (zero I/O)       │
└─────────────────────────────────────────────────────────────────────┘
```

- **`domain/`** não importa NADA de fora (nem `adapters`, nem `fastapi`, nem `httpx`, nem `sqlalchemy`, nem `anthropic`). Um teste (`tests/domain/test_architecture.py`) falha o build se isso for violado.
- **Porta** = interface `Protocol` (ex.: `CRMPort`, `WhatsAppPort`, `LLMPort`). O motor fala com a porta; o adapter implementa. Trocar de CRM/canal/LLM = trocar um campo na ficha, zero mudança no motor.
- **ACL (Anti-Corruption Layer):** todo vocabulário externo (`data_agendamento`, `tool_use`, `cache_control`) vive SÓ dentro do adapter respectivo. O domínio usa tipos limpos em inglês (`Appointment`, `ToolCall`, `Reply`).
- **Isolamento por construção (RN-03):** cada instância de adapter nasce amarrada a um tenant (recebe a config no construtor). Métodos das portas **não** recebem `tenant_id`.

### O fluxo de uma mensagem (ponta a ponta)

```
Z-API → POST /webhook/whatsapp/{token}  (api/webhook.py)
  → 200 imediato + processa em background (RN-45)
  → identifica tenant pelo token; filtra grupo/fromMe/newsletter; dedupe (RN-42)
  → DebounceBuffer agrupa rajada ~6s (RN-43), dentro do lock por conversa (RN-44)
  → MessagePipeline.handle (application/pipeline.py):
      • carrega Conversation + últimas N mensagens (RN-74)
      • grava a mensagem recebida no histórico
      • monta canal efetivo (shadow? gravação?)
      • ProcessIncomingMessage (o "maestro"):
          - se em handoff → IA calada (RN-31)
          - build_request: system prompt (cacheável) + resumo + últimas N + atual
          - LLMPort.respond → Reply (texto) ou ToolCall
          - ToolCall → assembly despacha para o use case real → resultado volta ao LLM
      • agenda/cancela follow-up (RN-51)
  → resposta enviada (ou, em shadow, sugerida ao time)
```

---

## 3. Estrutura do projeto (mapa comentado)

```
agente-whatsapp/
├── HANDOFF.md              ← você está aqui
├── PLANEJAMENTO.md         ← visão + roadmap por marcos
├── pyproject.toml          ← deps + config ruff/mypy/pytest
├── docker-compose.yml      ← Postgres (imagem pgvector/pgvector:pg16), porta 5439
├── Dockerfile              ← imagem única api+worker (migrations no boot)
├── alembic.ini + migrations/  ← schema versionado (1 migration consolidada)
├── .github/workflows/ci.yml   ← ruff + mypy + alembic + pytest (com pgvector)
│
├── src/agente/
│   ├── domain/             ← NÚCLEO PURO (zero I/O). Nunca importa de fora.
│   │   ├── enums.py            LeadPriority, HandoffStatus, EscalationTrigger, AppointmentStatus
│   │   ├── tenant.py           A FICHA: Tenant + Persona/Service/SchedulingPolicy/CRMConfig/
│   │   │                       ChannelConfig/LlmConfig/HandoffConfig/FollowUpConfig
│   │   ├── lead.py             LeadInfo (rascunho da conversa)
│   │   ├── conversation.py     Conversation + máquina de handoff (ACTIVE/PENDING/HUMAN)
│   │   ├── crm.py              Contact, AvailableSlot, AppointmentRequest, Appointment, HandoffTask
│   │   ├── llm.py              Tipos neutros do cérebro: LlmRequest, ToolSpec, ToolCall, Reply, TokenUsage
│   │   ├── messaging.py        IncomingMessage (canal-neutro), StoredMessage
│   │   ├── scheduling.py       ⭐ cálculo de disponibilidade (slot_grid, available_slots, is_slot_available)
│   │   └── ports.py            ⭐ TODAS as interfaces: CRMPort, WhatsAppPort, LLMPort,
│   │                           ConversationStorePort, SchedulerPort, KnowledgePort, EmbeddingPort
│   │
│   ├── application/        ← CASOS DE USO (orquestração). 1 classe = 1 use case com execute()
│   │   ├── identify_contact / qualify_lead / get_availability
│   │   ├── schedule_appointment / reschedule_appointment / cancel_appointment
│   │   ├── escalate.py         handoff na ordem do RN-31
│   │   ├── process_message.py  ⭐ o "maestro" (loop LLM ↔ tools)
│   │   ├── assembly.py         ⭐ traduz ToolCall do LLM → use case real (handlers)
│   │   ├── tools.py            catálogo neutro de ferramentas (RN-30: sem preço/desconto)
│   │   ├── prompt.py           system prompt renderizado da ficha + defesa anti-injection (RN-78)
│   │   ├── context_builder.py  montagem econômica: system + resumo + últimas N (RN-74/75)
│   │   ├── reminders.py        lembretes (RN-50)
│   │   ├── debounce.py         DebounceBuffer (RN-43)
│   │   ├── job_handlers.py     handlers do worker: reminder/auto_resume/follow_up
│   │   ├── pipeline.py         ⭐ MessagePipeline: a fiação de produção por tenant
│   │   └── errors.py           InvalidIntentError, MissingLeadDataError, SlotTakenError
│   │
│   ├── adapters/          ← A BORDA. Todo vocabulário externo vive aqui.
│   │   ├── crm/
│   │   │   ├── fake_crm.py      CRMPort em memória (dev/teste)
│   │   │   ├── factory.py       CRMConfig.type → adapter
│   │   │   └── trivus/          ⭐ TrivusCRM real (adapter, auth, dtos, trivus_time, errors)
│   │   ├── whatsapp/
│   │   │   ├── zapi.py / zapi_parser.py / incoming.py   Z-API envio+parse
│   │   │   ├── factory.py       ChannelConfig.type → adapter
│   │   │   ├── decorators.py    ShadowChannel (piloto), RecordingChannel (histórico)
│   │   │   └── fake_whatsapp.py
│   │   ├── llm/
│   │   │   ├── anthropic_llm.py Claude (prompt caching + token usage)
│   │   │   ├── openai_llm.py    OpenAI-compatible (GPT/Groq/Ollama)
│   │   │   ├── factory.py       LlmConfig.type → adapter
│   │   │   └── fake_llm.py      roteirizado p/ testes
│   │   ├── scheduler/
│   │   │   ├── postgres_scheduler.py  PostgresScheduler + JobWorker (SKIP LOCKED, retry)
│   │   │   └── fake_scheduler.py
│   │   ├── store/
│   │   │   ├── models.py        SQLAlchemy: conversations, messages, processed_messages,
│   │   │   │                    scheduled_jobs, knowledge_chunks
│   │   │   ├── postgres_store.py  ConversationStorePort real (dedupe, advisory lock, histórico)
│   │   │   └── fake_store.py
│   │   └── vectorstore/
│   │       ├── embedder.py      FakeEmbedder (dev) + OpenAIEmbedder
│   │       └── pgvector_store.py  RAG: ingest idempotente + search com isolamento por tenant
│   │
│   ├── api/
│   │   ├── webhook.py       create_app: endpoint do webhook + rate limit
│   │   └── main.py          entrypoint HTTP de produção (uvicorn agente.api.main:app)
│   ├── config/
│   │   ├── settings.py      pydantic-settings (envs)
│   │   ├── tenant_loader.py carrega ficha, valida no boot, resolve env: (RN-63)
│   │   └── tenants/         ⭐ AS FICHAS: revenda_veiculos.json, salao_demo.json
│   ├── utils/
│   │   ├── phone.py         variantes do 9º dígito BR (RN-22)
│   │   ├── chunking.py      chunking do RAG
│   │   ├── circuit_breaker.py  utilitário (fiação nos adapters pendente)
│   │   └── obs.py           log_event com telefone hasheado (LGPD)
│   ├── bootstrap.py        ⭐ COMPOSITION ROOT: fichas → fábricas → pipeline → webhook
│   ├── worker.py           entrypoint do worker de jobs
│   └── ingest.py           CLI: python -m agente.ingest <tenant> <arquivo>
│
├── tests/                 ← 52 arquivos; espelham src/ (domain/application/adapters/api/e2e/integration)
│   ├── domain/ application/ adapters/ api/ config/ utils/
│   ├── e2e/                ← fluxo completo com fakes (conversa e HTTP→resposta)
│   └── integration/        ← contra Postgres REAL (store, scheduler, pgvector)
│
└── docs/
    ├── SPEC.md             ⭐ regras RN-xx (fonte da verdade)
    ├── STATUS.md           compilado de estado
    ├── PENDENCIAS.md       ⭐ tudo que depende de humano (credenciais/acessos)
    ├── DEPLOY.md           guia Coolify
    ├── QUESTIONARIO_TRIVUS.md  perguntas que foram feitas ao time do trivus-api
    ├── plans/00-INDEX.md + 01..11  ⭐ os planos baby-step TDD
    └── trivus/             ⭐ respostas REAIS do trivus-api (INTEGRACAO_AGENTE, API_REFERENCE,
                            openapi.json, ONBOARDING) — insumo do Plano 08
```

Números: **77 arquivos .py em src (~3.665 linhas)**, **52 arquivos de teste**, **189 testes**.

---

## 4. Conceitos e regras de negócio (o essencial das RN)

Lista completa e canônica em [`docs/SPEC.md`](docs/SPEC.md). Resumo do que mais afeta o código:

**Núcleo agnóstico**
- **RN-01** Motor único; nada de ramo/CRM/LLM no código, só na ficha e adapters.
- **RN-02** Intents declaradas na ficha (revenda: `buy_vehicle`/`sell_vehicle`; salão: `haircut`/`nails`). Intent é `str` validada, não enum fixo.
- **RN-03** Isolamento por construção (adapter amarrado ao tenant).

**Agenda** (o cálculo mais crítico — `domain/scheduling.py`)
- **RN-10** Disponibilidade calculada NO agente (a partir das `working_hours` da ficha − ocupados que o CRM informa).
- **RN-11** Duração e capacidade **por serviço**. Exceção: `scheduling.shared_capacity: true` → capacidade da LOJA inteira (revenda, e CRMs que não registram o serviço — ex.: Trivus).
- **RN-12** Antecedência mínima configurável. **RN-13** Revalidação no commit (anti-corrida: duas conversas na última vaga). **RN-14** Datas SEMPRE tz-aware no domínio (naïve é erro de fronteira).

**Lead/handoff**
- **RN-20** Dados obrigatórios p/ agendar (nome, telefone, intent, data, hora). **RN-21** Qualificação gravada no CRM. **RN-22** Busca por telefone com variantes do 9º dígito + lid.
- **RN-30** Fronteira humana por design (sem tool de preço/desconto). **RN-31** Handoff numa ordem exata (PENDING antes de I/O → tarefa CRM → notifica time → mensagem ao cliente → auto-resume). **RN-32** Gatilhos de escalada.

**Canal** — **RN-40..45** (webhook porta de entrada, filtros, dedupe, debounce, lock, 200 imediato). **RN-40b** canal plugável pela ficha.

**Cérebro** — **RN-70** LLM plugável; **RN-71** dialeto neutro (ToolSpec/ToolCall/Reply); **RN-72** um adapter `openai_compat` cobre vários provedores; **RN-74** nunca mandar histórico inteiro; **RN-75** summarization buffer; **RN-76** prompt caching; **RN-77** extração estruturada; **RN-78** defesa anti prompt-injection; **RN-79** budget de tokens.

**Lembretes/produção** — **RN-50** 3 lembretes (véspera, manhã, 1h antes) no fuso do tenant; **RN-51** follow-up; **RN-60..66** ACL/segredos/async/idioma.

---

## 5. Como rodar (dev)

Pré-requisitos: Docker, `uv` (`https://docs.astral.sh/uv/`).

```bash
cd agente-whatsapp

# 1. Postgres (com pgvector) na porta 5439
docker compose up -d

# 2. Dependências
uv sync

# 3. Testes (unit + integração Postgres + e2e) — DEVE dar tudo verde
uv run pytest -q

# 4. Lint + tipos
uv run ruff check src tests
uv run mypy src

# 5. Migrations (schema do zero)
PYTHONPATH=src uv run alembic upgrade head

# 6. Subir a API (produção-like)
uv run uvicorn agente.api.main:app --reload
#    health: GET http://localhost:8000/health  → {"status":"ok"}
#    webhook: POST http://localhost:8000/webhook/whatsapp/<webhook_token-da-ficha>

# 7. Worker de jobs (lembretes/auto-resume/follow-up), em outro terminal
uv run python -m agente.worker

# 8. Ingerir base de conhecimento (RAG)
uv run python -m agente.ingest salao_demo caminho/para/faq.md
```

Sem `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` a API sobe (o LLM real só é chamado ao
conversar de verdade). Sem `OPENAI_API_KEY` o RAG usa `FakeEmbedder` (só dev).

---

## 6. Estado atual — o que está pronto

| Plano | Entrega | Status |
|---|---|---|
| 01 Domínio agnóstico | entidades + ports puros + teste de arquitetura | ✅ |
| 02 Agenda | slots por serviço/capacidade/fuso, anti-corrida | ✅ |
| 03 FakeCRM + fichas | fluxo em memória, fábrica de CRM | ✅ |
| 04 Use cases | qualificar/agendar/escalar + maestro (M1) | ✅ |
| 05 Persistência | Postgres, dedupe, advisory lock, Alembic | ✅ |
| 06 Canal Z-API | parser, sender, webhook, debounce (M2) | ✅ |
| 07 Cérebro plugável | Claude + GPT, contrato compartilhado | ✅ |
| 08 Adapter Trivus | 8 métodos, DTOs, auth, tradução de datas | 🟡 **código+testes prontos; falta só o smoke local (8.5)** |
| 09 Scheduler | worker Postgres + lembretes/auto-resume/follow-up | ✅ |
| 10 RAG | pgvector, ingestão idempotente, isolamento por tenant | ✅ |
| 11 Produção | bootstrap, worker, shadow, obs, Docker, CI | 🟡 **código pronto; falta deploy real** |

**189 testes** (unit + integração Postgres + e2e), ruff + mypy strict limpos.
Todos os commits são um por etapa, com mensagem Conventional Commits.

---

## 7. O que falta (mapa honesto — detalhes em `docs/PENDENCIAS.md`)

Nada abaixo é bloqueado por código — tudo depende de **credencial, acesso ou decisão**:

### Bloqueado em acessos
- **Plano 08.5 — smoke real do Trivus.** Clonar `trivusauto/trivus-api` (branch `develop` — tem o fix de datas), subir local (`docs/trivus/ONBOARDING.md`), criar um usuário de serviço **`role=client`** na loja seed, desligar `zapi_webhook_enabled`, rodar o roteiro criar→buscar→qualificar→agendar→reagendar→cancelar→handoff. Quando passar, fecha o **M3**.
- **Plano 11 — deploy no Coolify.** Infra escrita (`Dockerfile`, `.github/workflows/ci.yml`, `docs/DEPLOY.md`). Banco **DEVE** ser imagem `pgvector/pgvector:pg16`. Falta executar + preencher secrets.
- **Validação com provedores reais:** `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` (smoke do LLM), instância Z-API de teste + **um payload real** para confirmar os campos `text.message`/`messageId` do parser (hoje seguem a doc do Z-API — anotados como "a confirmar").

### Decisões pendentes
- **Provedor de embeddings** (OpenAI vs Voyage). Hoje: OpenAI se `OPENAI_API_KEY`, senão FakeEmbedder. Ao decidir: fixar a dimensão do vetor (`Vector(N)`) e criar índice **HNSW** (não ivfflat) só quando alguma base passar de ~10k chunks.
- **`handoff_user_id` por loja** (a quem atribuir no handoff).

### Melhorias já mapeadas (não bloqueiam)
- Fiar o `CircuitBreaker` nos adapters Z-API/CRM (utilitário pronto e testado).
- Pedir ao time do trivus-api o PR **`GET /crm/leads/{id}`** (barateia o append de observações — hoje é lista completa).
- Follow-up multiestágio, se o negócio pedir.
- `git push` para o GitHub (o CI já está escrito).

---

## 8. Como continuar o desenvolvimento (para a IA e para o humano)

### Método (não negociável)
1. **Leia a SPEC** antes de tocar em regra de negócio. Divergiu? Corrija a SPEC primeiro.
2. **TDD baby-step:** escreva o teste → veja falhar (pelo motivo certo) → implemente o mínimo → veja passar → `ruff`+`mypy` → commit. Um passo por vez.
3. **Nunca invente valor real** (token, payload, endpoint). Não tem? Pare e pergunte ao humano (é o que faz a integração ser confiável).
4. **Rode sempre no venv:** `uv run pytest` / `uv run ruff` / `uv run mypy`. Postgres no ar para os testes de integração.
5. Commits em Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`), um por etapa.

### O padrão que se repete (aprenda uma vez, aplique sempre)
Todos os três eixos externos seguem **porta + adapters + fábrica + escolha na ficha**:
- Porta em `domain/ports.py` (Protocol async, tipos do domínio).
- Adapters em `adapters/<eixo>/` (um por provedor) + um `fake_*` para testes.
- Fábrica `build_*` que lê `config.type` e devolve a instância.
- A ficha do tenant escolhe (`crm.type`, `channel.type`, `llm.type`).

### Receitas concretas

**Adicionar um novo CRM (ex.: `clube_amore`):**
1. Criar `adapters/crm/clube_amore/` implementando os 8 métodos da `CRMPort` (copie a estrutura de `adapters/crm/trivus/`: `dtos`, `auth`, `adapter`, `errors`).
2. Registrar em `adapters/crm/factory.py` (`if config.type == "clube_amore": ...`).
3. Testes com `respx` + fixtures reais da API do Clube Amore (proibido inventar).
4. Uma ficha `config/tenants/*.json` com `crm.type = "clube_amore"`.
5. Teste-guarda RN-60: o vocabulário do Clube Amore só pode existir dentro do pacote do adapter.

**Adicionar um provedor de LLM (ex.: `gemini`):** implemente `respond(request) -> Reply|ToolCall` traduzindo o dialeto do provedor; registre na `adapters/llm/factory.py`; a suíte de contrato compartilhada (`tests/adapters/test_llm_factory.py`) já testa paridade — parametrize o novo adapter nela.

**Adicionar o canal Evolution:** `adapters/whatsapp/evolution.py` (sender) + parser próprio que produz o mesmo `IncomingMessage`; registrar em `factory.py` e no dispatcher `incoming.py`.

**Onboard de um novo cliente:** só uma ficha JSON nova em `config/tenants/` (persona, intents, serviços/durações/capacidade, horários, handoff, `crm`/`channel`/`llm`). Segredos via `env:NOME` — nunca literais (RN-63). O `bootstrap.py` carrega tudo no boot; ficha com adapter faltante é pulada com warning (não derruba o boot).

### Gotchas aprendidos (evite repetir)
- **Fuso:** o trivus-api é tudo naïve-Brasília; o domínio é tz-aware. A tradução vive só em `adapters/crm/trivus/trivus_time.py`. `created_at/updated_at` do Trivus são UTC ISO.
- **Trivus duplica lead** e **não tem busca por telefone** nem `GET /crm/leads/{id}` — por isso `find` faz lista completa + filtro local, e `observacoes` é **append manual** (o PATCH sobrescreve).
- **`shared_capacity`** existe porque o Trivus não registra qual serviço é o agendamento — a ocupação da revenda conta contra a loja inteira.
- **Imagem do Postgres:** tem que ser `pgvector/pgvector:pg16` (o RAG precisa da extensão `vector`).
- **Docstrings contam para o RN-60:** o teste-guarda pega nome de campo externo até em comentário. Descreva sem citar `data_agendamento` & cia. fora do adapter.
- **mypy + SDKs externos:** anote `self._client: Any` nos adapters de LLM/embeddings para o mypy não seguir os tipos do SDK (o adapter é a fronteira).

---

## 9. Mapa de documentos (por onde começar a ler)

| Quero… | Leia |
|---|---|
| Entender a ideia e o roadmap | `PLANEJAMENTO.md` (raiz) |
| As regras de negócio (fonte da verdade) | `docs/SPEC.md` |
| O passo a passo de implementação (baby-steps) | `docs/plans/00-INDEX.md` → `01..11` |
| Estado atual resumido | `docs/STATUS.md` |
| O que depende de mim (humano) | `docs/PENDENCIAS.md` |
| Integrar/entender o Trivus | `docs/trivus/INTEGRACAO_AGENTE.md` (Q&A com payloads reais) + `API_REFERENCE.md` + `openapi.json` |
| Subir o trivus-api local | `docs/trivus/ONBOARDING.md` |
| Fazer deploy | `docs/DEPLOY.md` |

---

## 10. Glossário rápido

- **Tenant** — o negócio cliente do agente (uma revenda, um salão). Dono de uma ficha.
- **Ficha** — o JSON de configuração do tenant (`config/tenants/*.json`).
- **Porta / Adapter** — interface (domínio) / implementação (borda). O coração do hexagonal.
- **ACL** — Anti-Corruption Layer: o adapter que traduz o mundo externo ↔ tipos limpos.
- **Maestro** — `ProcessIncomingMessage`: orquestra o loop LLM ↔ ferramentas.
- **Pipeline** — `MessagePipeline`: a fiação de produção de uma mensagem, por tenant.
- **Shadow mode** — piloto: a IA só *sugere* (mensagem vai ao time), não fala com o cliente.
- **RN-xx** — regra de negócio numerada na SPEC.
- **Marco (M1..M5)** — agrupamento de planos (M1 motor com fakes … M5 produção).

---

*Fim do handoff. Se algo aqui divergir do código, o código + a SPEC mandam — e
então atualize este arquivo. Boa continuação. 🚀*
