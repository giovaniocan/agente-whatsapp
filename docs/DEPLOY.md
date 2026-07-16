# Deploy (Coolify) — Plano 11

> Espelha o padrão do trivus-api: CI verde na main → Coolify rebuilda pelo
> Dockerfile; migrations rodam no boot do container.

## Serviços (3)

| Serviço | Origem | Comando |
|---|---|---|
| **db** | Postgres gerenciado do Coolify — **imagem `pgvector/pgvector:pg16`** (o RAG precisa da extensão `vector`) | — |
| **api** | este repo, `Dockerfile` | CMD default (migrations + uvicorn, porta 8000) |
| **worker** | este repo, mesmo `Dockerfile` | sobrescrever CMD: `python -m agente.worker` |

## Variáveis de ambiente

| Env | Serviço | O quê |
|---|---|---|
| `DATABASE_URL` | api + worker | `postgresql+asyncpg://user:pass@db:5432/agente` |
| `TENANTS_DIR` | api + worker | default `src/agente/config/tenants` (fichas commitadas) |
| `ANTHROPIC_API_KEY` | api | cérebro (fichas com `llm.type=anthropic`) |
| `OPENAI_API_KEY` | api (+ ingestão) | llm `openai_compat` e/ou embeddings do RAG |
| `ZAPI_TOKEN_<TENANT>` | api + worker | um por ficha que referencie `env:ZAPI_TOKEN_...` |
| `TRIVUS_TOKEN_<LOJA>` | api + worker | quando o adapter Trivus existir (plano 08) |
| `DEBOUNCE_SECONDS` / `WEBHOOK_RATE_LIMIT_PER_MINUTE` | api | opcionais (defaults 6.0 / 120) |

Segredos SEMPRE por env (RN-63) — as fichas commitadas só carregam `env:NOME`.

## Passo a passo

1. Criar o Postgres (imagem pgvector) e copiar a `DATABASE_URL`.
2. Criar o app **api** apontando para o repo (Dockerfile). Setar envs. Deploy —
   o boot roda `alembic upgrade head` e sobe o uvicorn.
3. Criar o app **worker** com o mesmo repo/Dockerfile, CMD `python -m agente.worker`.
4. Health check: `GET https://<api>/health` → `{"status":"ok"}`.
5. Apontar o webhook "ao receber" da instância Z-API do tenant para
   `POST https://<api>/webhook/whatsapp/<webhook_token-da-ficha>`.
6. Ingerir a base de conhecimento: `python -m agente.ingest <tenant_id> faq.md`
   (rodar de dentro do container api, ou local com a DATABASE_URL de prod).

## Piloto (shadow mode)

Na ficha do tenant piloto: `"mode": "shadow"` — a IA NÃO fala com o cliente;
toda resposta vira sugestão no WhatsApp do time (`handoff.team_phone`).
Critérios para virar `"autonomous"`: zero violações da RN-30, agendamentos
válidos e taxa de resposta correta acordada com o cliente (docs/PENDENCIAS.md).

## Observabilidade

- Logs estruturados; telefone SEMPRE hasheado (LGPD — testado).
- Jobs com falha ficam `status=failed` na tabela `scheduled_jobs` (alertar nisso).
- Rate limit do webhook: 429 acima do limite por tenant.
