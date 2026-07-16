# Plano 08 — Adapter TrivusCRM (ACL contra o trivus-api)

**Objetivo:** o adapter real. Traduz `CRMPort` ↔ REST do trivus-api. Fecha o **M3**.
**Regras cobertas:** RN-40, RN-60, RN-61, RN-62, RN-64, RN-65.

> **✅ QUESTIONÁRIO RESPONDIDO (16/07/2026)** — respostas com payloads reais em
> [`../trivus/INTEGRACAO_AGENTE.md`](../trivus/INTEGRACAO_AGENTE.md) (+ API_REFERENCE,
> openapi.json, ONBOARDING na mesma pasta). As tarefas abaixo já refletem o
> comportamento REAL confirmado. Rodar contra a branch **develop** (contém o fix
> do 500 de datas no PATCH de agendamento).

## Design real (o que as respostas mudaram)

| Tema | Realidade confirmada | Consequência no adapter |
|---|---|---|
| Auth | `POST /auth/login` {email,password} → JWT 7d, SEM refresh | re-login no 401; ficha: `settings.email` + senha via `api_key: env:TRIVUS_PASSWORD_<LOJA>` |
| Usuário de serviço | **`role=client`** por loja (shop_user só vê leads próprios) | criado via `/admin/users` + `PUT /admin/users/{id}/stores`; e-mail com TLD real |
| Escopo | `store_id` em **query**; token não restringe | `settings.store_id` fixo em prod; dev/seed: descobrir via `GET /stores/mine` |
| Busca por telefone | **NÃO EXISTE** — `GET /crm/leads?store_id=` devolve a lista completa | filtrar localmente com `phone_variants` (já temos) |
| Criar lead | **`stage_id` OBRIGATÓRIO**; sem auto-etapa, sem round-robin | `GET /crm/funnels?store_id=` → stage de menor `sort_order` → **cachear por loja** |
| Dedupe | **API DUPLICA** | dedupe é nosso: find-then-create (já é o fluxo) + lock por conversa |
| Agendamento | `PATCH /crm/leads/{id}/agendamento` — data `YYYY-MM-DD`, hora `HH:MM`; `null`s cancelam; `agendado_por`/`data_marcacao` são do back (só no 1º) | tradução tz-aware ↔ naïve-Brasília (RN-62) |
| Agenda do dia | `GET /agenda?store_id&apply_to=agendamento&preset=custom&from=D&to=D&page_size=100` paginado `{items,total,page}` | paginar até `page*page_size >= total` |
| PATCH genérico | `exclude_none` → **null NÃO limpa campo** | nunca tentar "zerar" via PATCH /crm/leads/{id} |
| Handoff | sem endpoint de nota; `observacoes` **SOBRESCREVE**; **não há `GET /crm/leads/{id}`** | append manual: lista → acha → concatena `[IA→humano] ...` → PATCH (corrida aceita v1); `assigned_to` só se `settings.handoff_user_id` na ficha |
| Feature gate | só nas leituras: `crm.kanban` (leads/funnels), `agenda` | 403 `{"error":"feature_locked","feature_key":...}` → `FeatureLockedError`, sem retry |
| Erros | 400/401/403/404 = `{"error": "..."}`; **422 = `{"detail":[...]}`** (FastAPI) | tratar os DOIS formatos na fronteira |
| Fuso | tudo naïve Brasília; `created_at/updated_at` UTC ISO | fixo `America/Sao_Paulo` |
| Rate limit | não há | mesmo assim: lista completa por find é pesada → otimização futura c/ TTL curto (anotar, não fazer) |
| Piloto | `PATCH /admin/stores/{id}` `{"zapi_webhook_enabled": false}` | checklist do smoke/go-live |

## Tarefa 8.1 — Fixtures reais + DTOs

- [ ] Copiar de `docs/trivus/INTEGRACAO_AGENTE.md` os JSONs reais (login, lead completo,
      funnels, agenda paginada, erros 4xx/422) para `tests/adapters/trivus/fixtures/`
- [ ] Teste: DTOs Pydantic (`TrivusLead`, `TrivusLogin`, `TrivusFunnel`, `TrivusAgendaPage`)
      parseiam as fixtures; campo inesperado → erro claro (RN-61). DTOs PRIVADOS (RN-60)
- [ ] Commit: `feat(trivus): boundary DTOs from real API fixtures`

## Tarefa 8.2 — Auth de serviço (RN-64)

- [ ] Teste (respx): login {email,password} → guarda JWT; 401 em chamada → re-login UMA
      vez e repete; 403 feature_locked → `FeatureLockedError` (sem retry)
- [ ] Ficha: `crm.settings = {store_id, email, handoff_user_id?}`; senha via
      `crm.api_key = env:TRIVUS_PASSWORD_<LOJA>` (loader já resolve)
- [ ] Commit: `feat(trivus): service-user JWT auth with relogin-on-401`

## Tarefa 8.3 — Tradução de tempo (RN-62)

- [ ] Teste: `2026-07-20T14:30-03:00` (domínio) ↔ `{"data_agendamento":"2026-07-20",
      "hora_agendamento":"14:30"}`; volta aceita `"14:30:00"`; caso de virada de dia
      em UTC não muda a data local
- [ ] Commit: `feat(trivus): tz-aware <-> Brasília-naive translation`

## Tarefa 8.4 — Os 8 métodos da CRMPort (respx + fixtures reais)

- [ ] `find_contact_by_phone`: GET lista completa → filtro local c/ `phone_variants`
- [ ] `create_contact`: resolve+cacheia stage inicial (funnels) → POST c/ `stage_id`
- [ ] `update_lead_qualification`: PATCH {qualificado, urgencia_venda, observacoes, origem_mkt}
- [ ] `get_appointment`/`get_scheduled_appointments`: GET /agenda paginado (custom from=to=dia)
- [ ] `create_appointment` / `cancel_appointment` (nulls) / `reschedule_appointment`
- [ ] `create_handoff_task`: [assigned_to se configurado] + append em observacoes
- [ ] Teste RN-60 (grep): vocabulário Trivus só existe em `adapters/crm/trivus/`
- [ ] Registrar na fábrica: `type="trivus"` → TrivusCRM; bootstrap passa a carregar a revenda
- [ ] Commit por método

## Tarefa 8.5 — Smoke local (com humano junto)

**Pré-requisito:** clonar `trivusauto/trivus-api` (branch develop) e subir local
(`docs/trivus/ONBOARDING.md` — docker + seed). Sem staging por ora.

- [ ] Criar usuário IA (client) + vincular à loja seed; desligar `zapi_webhook_enabled`
- [ ] Roteiro: criar lead → buscar por telefone → qualificar → agendar → ver no front →
      reagendar → cancelar → handoff (assigned_to + observações)
- [ ] Marcar ✅ no 00-INDEX (fecha M3)

## Melhorias a pedir ao time do trivus-api (não bloqueiam)

1. **`GET /crm/leads/{id}`** — barateia o append de observações e qualquer refresh (hoje: lista completa). PR pequeno, alto valor p/ o agente.
2. `shop_role` no `GET /stores/{id}/team` — só se quisermos rotear handoff por papel (alternativa atual: `handoff_user_id` fixo na ficha).
3. Busca por telefone server-side — só quando alguma loja tiver milhares de leads.
