# Plano 02 — Agenda: cálculo de disponibilidade

**Objetivo:** o serviço de domínio que calcula slots livres — a peça mais crítica e
mais testável do sistema. Puro (zero I/O): recebe a ficha + lista de ocupados, devolve slots.
**Regras cobertas:** RN-10, RN-11, RN-12, RN-13 (parte), RN-14.

> Serviço de domínio (DDD): lógica que não pertence a UMA entidade — pertence à colaboração
> entre `SchedulingPolicy`, `Service` e `Appointment`. Vive em `domain/scheduling.py`.

## Tarefa 2.1 — Grade de slots do dia

- [ ] Teste: tenant com working_hours seg 09:00–18:00, serviço 60min → `slot_grid(day)`
      devolve 9 slots tz-aware (09h…17h) para uma segunda; 0 slots para domingo
- [ ] Ver falhar → implementar `slot_grid(policy, service, day)` com `zoneinfo`
- [ ] Teste: serviço de 45min → slots a cada 45min (a grade é do SERVIÇO, RN-11)
- [ ] Teste: duas janelas no mesmo dia (09–12 e 14–18) → sem slots no almoço
- [ ] Teste **`working_hours` é lista arbitrária por tenant** (não fixa): cliente A
      08:00–16:00 direto (1 janela/dia); cliente B 06:00–12:00 + 16:00–18:00 (2 janelas,
      4h de almoço); cliente C com dias da semana diferentes entre si (sábado só até
      12:00, domingo sem janela nenhuma = fechado). As três fichas são fixtures de teste,
      não casos especiais no código — a função não sabe que "almoço" existe, só soma janelas
- [ ] Commit: `feat(domain): per-service slot grid from working hours (RN-10, RN-11)`

## Tarefa 2.2 — Capacidade e ocupação

- [ ] Teste: capacidade 3, dois agendamentos às 10h → slot das 10h AINDA disponível;
      três às 10h → indisponível
- [ ] Ver falhar → implementar `available_slots(policy, service, day, busy: list[Appointment])`
- [ ] Teste: capacidade conta POR SERVIÇO (1 corte às 10h não consome a vaga da manicure)
      — decide: ocupação é casada por intent do appointment
- [ ] Teste: agendamento que ATRAVESSA slots (serviço 90min às 10h) bloqueia 10h e 11h
- [ ] Commit: `feat(domain): capacity-aware availability per service (RN-11)`

## Tarefa 2.3 — Antecedência mínima e "agora"

- [ ] Teste: `min_notice_minutes=0`, agora=10:30 → slot das 10h NÃO aparece (já passou),
      11h aparece; `min_notice_minutes=120` → só a partir de 12:30→13h
- [ ] Ver falhar → implementar corte por `now` (injetado como parâmetro — nunca
      `datetime.now()` dentro da função; determinismo de teste)
- [ ] Teste: fuso — `now` em UTC e loja em São Paulo: o corte respeita o fuso da loja (RN-14)
- [ ] Commit: `feat(domain): min-notice and now-cutoff in store timezone (RN-12, RN-14)`

## Tarefa 2.4 — Validação de um slot específico (base do RN-13)

- [ ] Teste: `is_slot_available(policy, service, start, busy, now)` — true/false para os
      cenários acima (será chamada de novo no COMMIT do agendamento, plano 04)
- [ ] Ver falhar → implementar reutilizando as funções anteriores
- [ ] Commit: `feat(domain): single-slot validation for commit-time recheck (RN-13)`

## Critério de pronto

- [ ] Cobertura total dos cenários: grade, capacidade por serviço, atravessamento,
      antecedência, fuso, dia sem expediente
- [ ] Zero I/O e zero import de fora (teste de arquitetura continua verde)
- [ ] Marcar ✅ no 00-INDEX
