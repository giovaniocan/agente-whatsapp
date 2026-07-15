# Plano 04 — Use cases de atendimento (application/)

**Objetivo:** a orquestração. 1 classe = 1 caso de uso com `execute()`, dependências
recebidas no construtor (ports), testadas com fakes. Fecha o **M1**.
**Regras cobertas:** RN-13, RN-20, RN-21, RN-30, RN-31, RN-32, RN-50 (agendar jobs).

## Tarefa 4.1 — IdentifyOrCreateContact

- [ ] Teste: telefone já existe → devolve o Contact existente (não duplica);
      não existe → cria com nome provisório
- [ ] Ver falhar → implementar `application/identify_contact.py`
- [ ] Commit: `feat(app): IdentifyOrCreateContact use case`

## Tarefa 4.2 — QualifyLead (RN-21)

- [ ] Teste: com intent válida da ficha → chama `update_lead_qualification` do port com
      intent/priority/notes; intent fora da ficha → `InvalidIntentError` (RN-02)
- [ ] Ver falhar → implementar
- [ ] Commit: `feat(app): QualifyLead validates intent against tenant config`

## Tarefa 4.3 — GetAvailability + ScheduleAppointment (RN-13, RN-20)

- [ ] Teste: `GetAvailability(intent, day)` → usa serviço da intent + ocupados do port +
      `available_slots` do plano 02
- [ ] Teste RN-20: agendar sem nome completo OU sem intent → `MissingLeadDataError`
      listando os campos que faltam (o LLM usa essa lista para perguntar)
- [ ] Teste RN-13 (o mais importante): fluxo — consulta slots, OUTRO agendamento entra
      (simulado no fake), commit do slot cheio → `SlotTakenError` com alternativas;
      commit de slot válido → `Appointment` criado
- [ ] Ver falhar → implementar `ScheduleAppointment` revalidando com `is_slot_available`
      no momento do `create_appointment`
- [ ] Teste: ao agendar, agenda os 3 lembretes via `SchedulerPort` (RN-50) — verificar
      no FakeScheduler os horários: D-1, manhã do dia (09:00 local), H-1
- [ ] Commit: `feat(app): availability + schedule with commit-time recheck and reminders`

## Tarefa 4.4 — Reschedule / Cancel

- [ ] Teste: reagendar valida o novo slot (mesma RN-13) e RECALCULA lembretes;
      cancelar remove agendamento e cancela lembretes
- [ ] Ver falhar → implementar
- [ ] Commit: `feat(app): reschedule and cancel with reminder recalculation (RN-50)`

## Tarefa 4.5 — EscalateToHuman (RN-31, na ordem)

- [ ] Teste: dado Conversation ACTIVE + trigger → (1) status vira PENDING **antes** de
      qualquer I/O; (2) HandoffTask contém histórico-resumo, lead, reason, routing_hint;
      (3) `create_handoff_task` chamado; (4) `send_text` ao time; (5) `send_text` ao
      cliente com a mensagem da ficha; (6) job de auto-resume agendado (X horas da ficha)
- [ ] Teste de ordem: se `create_handoff_task` falhar, time é notificado MESMO ASSIM
      (fallback) e o status permanece PENDING — nunca deixar a IA voltar sozinha por erro
- [ ] Ver falhar → implementar `application/escalate.py`
- [ ] Commit: `feat(app): EscalateToHuman following RN-31 ordering with failure fallback`

## Tarefa 4.6 — ProcessIncomingMessage (o maestro)

- [ ] Teste: conversa PENDING/HUMAN → IA NÃO responde (mensagem só é armazenada);
      ACTIVE → chama `LLMPort.respond` com as tools permitidas
- [ ] Teste: LLM devolve tool_call `schedule_appointment` → use case executado e resultado
      devolvido ao LLM para redigir a resposta final; LLM devolve texto → envia via
      `WhatsAppPort`
- [ ] Teste RN-30: o tool-set passado ao LLM NUNCA contém desconto/preço/financiamento —
      teste literal da lista de tools
- [ ] Ver falhar → implementar `application/process_message.py`
- [ ] Commit: `feat(app): ProcessIncomingMessage orchestrator (RN-30 toolset boundary)`

## Critério de pronto (fecha M1)

- [ ] Teste e2e com fakes: mensagem chega → contato criado → qualificado → slots →
      agendado → lembretes agendados → handoff por pedido explícito → IA silencia
- [ ] `pytest` + `ruff` + `mypy` verdes; marcar ✅ no 00-INDEX
