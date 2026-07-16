# STATUS — Agente WhatsApp (compilado em 15/07/2026)

> Resumo executivo do estado do projeto após a sessão dos Planos 09/10/11.
> Detalhes: [SPEC.md](SPEC.md) · [plans/00-INDEX.md](plans/00-INDEX.md) ·
> [PENDENCIAS.md](PENDENCIAS.md) · [DEPLOY.md](DEPLOY.md)

## Placar geral

| Plano | Entrega | Status |
|---|---|---|
| 01 Domínio agnóstico | entidades + ports puros + teste de arquitetura | ✅ |
| 02 Agenda | slots por serviço/capacidade/fuso, anti-corrida | ✅ |
| 03 FakeCRM + fichas | fluxo completo em memória, fábrica de CRM | ✅ |
| 04 Use cases | qualificar, agendar, escalar, maestro (M1) | ✅ |
| 05 Persistência | Postgres, dedupe, advisory lock, Alembic | ✅ |
| 06 Canal Z-API | parser, sender, webhook, debounce (M2) | ✅ |
| 07 Cérebro plugável | adapters Claude + GPT, contrato compartilhado | ✅ |
| **08 Adapter Trivus** | tradução p/ trivus-api real | ⬜ **bloqueado** (acesso ao repo/staging) |
| 09 Scheduler | worker Postgres + lembretes/auto-resume/follow-up | ✅ |
| 10 RAG | pgvector, ingestão idempotente, isolamento por tenant | ✅ |
| 11 Produção | bootstrap, worker, shadow, obs, Docker, CI | 🟡 código pronto; **deploy real pendente** |

**Qualidade:** 172 testes (unit + integração Postgres + e2e) · ruff limpo · mypy strict limpo.
**Rodar local:** `docker compose up -d` → `uv run alembic upgrade head` (com `PYTHONPATH=src`) → `uv run uvicorn agente.api.main:app` · worker: `uv run python -m agente.worker`.

## O que entrou nesta sessão (09/10/11)

### Plano 09 — Scheduler (✅)
- `PostgresScheduler` + `JobWorker`: jobs vencidos com `FOR UPDATE SKIP LOCKED`
  (réplicas não duplicam), retry com backoff, falha **visível** (`status=failed`).
- Handlers: `reminder` (mensagem no fuso do tenant), `auto_resume` (respeita
  humano no comando), `follow_up` (só com IA ativa).

### Plano 10 — RAG (✅)
- Chunking com overlap; `EmbeddingPort` com `FakeEmbedder` (dev/demo) e
  `OpenAIEmbedder` (real, testado com SDK mockada).
- `PgVectorKnowledgeStore`: ingestão idempotente (hash), busca por cosine com
  **isolamento duro por tenant** (testado); tool `search_knowledge` no cérebro
  (base vazia → "não invente" — reforço da RN-30).
- CLI: `python -m agente.ingest <tenant> <arquivo>`.
- Migration única reproduz o schema do zero (5 tabelas + extensão vector).

### Plano 11 — Produção (🟡 código pronto)
- **Bootstrap** (`agente/bootstrap.py`): composition root real — carrega fichas,
  monta CRM/LLM/canal por tenant, pipeline → debounce → webhook. Tenant com
  adapter pendente (revenda/trivus) é pulado com warning, sem derrubar o boot.
- **Pipeline** (`application/pipeline.py`): histórico in/out, cancela/agenda
  follow-up, salva conversa — testado com fakes.
- **Shadow mode (11.5)**: `"mode": "shadow"` na ficha → resposta vira sugestão
  no WhatsApp do time; cliente não recebe (lembretes idem).
- **Observabilidade (11.3)**: `log_event` hasheia telefone (LGPD, testado);
  rate limit do webhook (429).
- **Resiliência (11.4)**: `CircuitBreaker` utilitário testado (fiação nos
  adapters ainda pendente — ver pendências).
- **Infra**: `Dockerfile` (api+worker, migrations no boot), `.github/workflows/ci.yml`
  (ruff+mypy+alembic+pytest com pgvector), `docs/DEPLOY.md` (Coolify).

## Erros encontrados e corrigidos nesta sessão
1. **DebounceBuffer não repassava o telefone** ao downstream — o pipeline de
   produção precisa dele. Assinatura corrigida (`(tenant, phone, texto)`) + testes.
2. **Imagem do Postgres sem pgvector** — trocada para `pgvector/pgvector:pg16`
   (dev, CI e guia de deploy); volume recriado (warning de collation eliminado).
3. **Migration autogerada sem a extensão/import** do pgvector — patch aplicado
   e upgrade validado num banco zerado.
4. Ficha do salão sem `webhook_token` — adicionada (senão o tenant fica
   inacessível via webhook).

## O que falta (mapa honesto)
- **Plano 08 (TrivusCRM)** — bloqueado em VOCÊ: acesso ao repo `trivusauto/trivus-api`
  (API_REFERENCE + staging) e usuário de serviço "IA". O motor já está pronto
  para plugá-lo (fábrica + bootstrap toleram a chegada).
- **Deploy real no Coolify** — infra escrita; falta executar (acessos/secrets).
- **Validação com provedores reais** — chaves LLM + instância Z-API + payload
  real p/ confirmar campos do parser.
- Fiação do circuit breaker nos adapters; índice ivfflat quando o provedor de
  embeddings for definido; follow-up multiestágio se o negócio pedir.

Checklist completo e atualizado: [PENDENCIAS.md](PENDENCIAS.md).
