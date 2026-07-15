# Plano 11 — Produção: deploy, observabilidade e piloto

**Objetivo:** operável em produção com segurança e escala. Fecha o **M5**.
**Regras cobertas:** RN-63, RN-65 + requisitos de operação.

## Tarefa 11.1 — Containers e CI

- [ ] Dockerfile (multi-stage, uv) para api e worker; compose de produção local
- [ ] GitHub Actions: ruff + mypy + pytest (Postgres de serviço) a cada push —
      espelhar o pipeline do trivus-api
- [ ] Commit: `chore: dockerfiles and CI pipeline`

## Tarefa 11.2 — Deploy Coolify

- [ ] App api + app worker + Postgres gerenciado; migrations no boot do container
- [ ] Envs documentadas em `docs/DEPLOY.md`: DATABASE_URL, ANTHROPIC_API_KEY,
      tokens Z-API por tenant, credenciais do usuário-IA do trivus-api (RN-63)
- [ ] Webhook Z-API do tenant piloto apontado para a URL pública `/webhook/whatsapp/{token}`
- [ ] Commit: `docs: deploy guide (Coolify)`

## Tarefa 11.3 — Observabilidade e proteção

- [ ] Logs estruturados (json): tenant_id, conversation_id, phone HASHEADO (LGPD — nunca
      telefone em claro), latência, tokens/custo por conversa
- [ ] Métrica diária por tenant: conversas, agendamentos, escaladas, custo LLM
- [ ] Rate limit no webhook (por token) e tamanho máximo de payload
- [ ] Teste: log de uma conversa completa NÃO contém telefone em claro
- [ ] Commit: `feat(ops): structured logging, cost metrics, webhook protection`

## Tarefa 11.4 — Resiliência

- [ ] Teste: trivus-api fora do ar → agente avisa que confirmará depois e enfileira a
      ação como job (retry); Z-API falhou o envio → retry do plano 06
- [ ] Circuit breaker simples por adapter (N falhas → abre por T segundos)
- [ ] Commit: `feat(ops): degraded-mode queueing and circuit breaker`

## Tarefa 11.5 — Piloto (shadow mode)

- [ ] Flag por tenant `mode: shadow | autonomous` — em shadow, a IA NÃO envia ao cliente;
      envia a RESPOSTA SUGERIDA ao grupo do time (aprovação humana)
- [ ] 1 loja real em shadow por 1–2 semanas; revisar transcripts, ajustar prompt/fichas
- [ ] Critérios de saída do shadow (definir com o cliente): taxa de resposta correta,
      zero violações da RN-30, agendamentos válidos
- [ ] Virar `autonomous` → **produção de verdade** 🎉
- [ ] Marcar ✅ no 00-INDEX (fecha M5)
