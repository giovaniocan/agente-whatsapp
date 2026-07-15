# Plano 08 — Adapter TrivusCRM (ACL contra o trivus-api)

**Objetivo:** o adapter real. Traduz `CRMPort` ↔ REST do trivus-api. Fecha o **M3**.
**Regras cobertas:** RN-40, RN-60, RN-61, RN-62, RN-64, RN-65.
**Pré-requisito humano:** acesso ao repo `trivusauto/trivus-api` (docs/API_REFERENCE.md
e /openapi.json de staging) + usuário de serviço "IA" criado na loja piloto.
**⚠️ Não inventar endpoint/campo:** cada payload de teste é copiado do API_REFERENCE.

## Tarefa 8.1 — Contratos (DTOs internos do adapter)

- [ ] Copiar do API_REFERENCE os JSONs reais de: login, lead (GET/POST/PATCH), agenda →
      fixtures em `tests/adapters/trivus/fixtures/`
- [ ] Teste: DTOs Pydantic (`TrivusLead`, `TrivusLoginResponse`…) parseiam as fixtures;
      campo inesperado/faltante → erro claro (RN-61). DTOs são PRIVADOS do adapter (RN-60)
- [ ] Commit: `feat(trivus): boundary DTOs validated against real API fixtures`

## Tarefa 8.2 — Auth de serviço (RN-64)

- [ ] Teste (respx): login → guarda JWT; chamada com 401 → re-login UMA vez e repete;
      403 `feature_locked` → `FeatureLockedError` (sem retry)
- [ ] Ver falhar → implementar `TrivusAuth` (token cache por instância/tenant)
- [ ] Commit: `feat(trivus): service-user JWT auth with refresh-on-401`

## Tarefa 8.3 — Tradução de tempo (RN-62) — o teste mais importante do plano

- [ ] Teste: `2026-07-20T14:00-03:00` (domínio) → `data_agendamento="2026-07-20"` +
      `hora_agendamento="14:00:00"` (Trivus); e a volta. Incluir caso de virada de dia
      em UTC (23h em SP = dia seguinte em UTC — NÃO pode mudar a data local)
- [ ] Ver falhar → implementar `trivus_time.py` dentro do adapter
- [ ] Commit: `feat(trivus): tz-aware <-> Brasília-naive time translation (RN-62)`

## Tarefa 8.4 — Os 8 métodos da CRMPort

- [ ] Para CADA método, na ordem, com respx + fixtures reais (teste → falhar → implementar):
      `find_contact_by_phone` (variantes 9º dígito na query) → `create_contact` →
      `update_lead_qualification` → `get_scheduled_appointments` → `create_appointment` →
      `cancel_appointment` → `reschedule_appointment` → `create_handoff_task`
      (assigned_to + observações/activity — conforme o que a API expõe)
- [ ] Teste RN-60: grep no repo — vocabulário Trivus (`telefone`, `data_agendamento`,
      `crm_funnel`) só existe dentro de `adapters/crm/trivus/`
- [ ] Registrar na fábrica: `type="trivus"` → TrivusCRM
- [ ] Commit por método: `feat(trivus): <método> against trivus-api`

## Tarefa 8.5 — Smoke em staging (com humano junto)

- [ ] Rodar contra staging real: criar lead de teste, agendar, ver no Trivus, reagendar,
      cancelar, escalar. Checklist manual documentado em `docs/SMOKE_TRIVUS.md`
- [ ] Marcar ✅ no 00-INDEX (fecha M3)
