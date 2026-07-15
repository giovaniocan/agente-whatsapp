# Plano 09 — Scheduler: lembretes, auto-resume e follow-up

**Objetivo:** o worker que executa `scheduled_jobs` (tabela do plano 05).
**Regras cobertas:** RN-31 (auto-resume), RN-50, RN-51.

## Tarefa 9.1 — Worker de jobs

- [ ] Teste: job `due` (run_at <= now) → executado e marcado `done`; falha → `retrying`
      com backoff e máx tentativas → `failed` (nunca some silenciosamente)
- [ ] Ver falhar → implementar loop asyncio (`adapters/scheduler/worker.py`) com
      `FOR UPDATE SKIP LOCKED` (múltiplas réplicas sem duplicar execução)
- [ ] Commit: `feat(scheduler): job worker with skip-locked and retry`

## Tarefa 9.2 — Lembretes (RN-50)

- [ ] Teste: agendamento sáb 15h (SP) → jobs em sex 15h, sáb 09h, sáb 14h (fuso do tenant);
      agendamento feito HOJE às 10h para HOJE 15h → só os lembretes futuros (14h)
- [ ] Teste: executar job de lembrete → `send_text` com template da ficha;
      reagendou/cancelou → jobs antigos cancelados (plano 04 já criou os hooks)
- [ ] Ver falhar → implementar handler `reminder`
- [ ] Commit: `feat(scheduler): 3-touch reminders in tenant timezone (RN-50)`

## Tarefa 9.3 — Auto-resume do handoff (RN-31.6)

- [ ] Teste: conversa PENDING + job auto_resume vence → status ACTIVE + log; se um humano
      respondeu nesse meio-tempo (status HUMAN) → job vira no-op
- [ ] Ver falhar → implementar handler `auto_resume`
- [ ] Commit: `feat(scheduler): handoff auto-resume honoring human takeover`

## Tarefa 9.4 — Follow-up de lead frio (RN-51)

- [ ] Teste: conversa ACTIVE sem resposta do cliente há N horas (ficha) → job de follow-up
      dispara UMA mensagem e agenda o próximo estágio (máx da ficha; depois desiste)
- [ ] Ver falhar → implementar handler `follow_up`
- [ ] Commit: `feat(scheduler): configurable cold-lead follow-up (RN-51)`

## Critério de pronto

- [ ] Worker roda no compose junto com a API; jobs sobrevivem a restart (estão no banco)
- [ ] Marcar ✅ no 00-INDEX
