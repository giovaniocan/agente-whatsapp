# Plano 03 — FakeCRM, fichas de tenant e fábrica

**Objetivo:** primeiro adapter (em memória) cumprindo a `CRMPort`; fichas JSON reais;
fábrica que resolve `crm.type` → adapter. Ao final, o fluxo de agendamento roda inteiro
sem nada externo.
**Regras cobertas:** RN-03, RN-22, RN-61, RN-63.

## Tarefa 3.1 — FakeCRM

- [ ] Teste: `create_contact` → devolve `Contact` com id; `find_contact_by_phone` acha;
      telefone inexistente → `None`
- [ ] Ver falhar → implementar `adapters/crm/fake_crm.py` (dicts em memória)
- [ ] Teste RN-22: contato salvo como `44999999999` é encontrado buscando `4499999999`
      (variantes do 9º dígito — portar a lógica de `phoneMatchVariants` p/ `utils/phone.py`
      com testes próprios)
- [ ] Teste: `create_appointment` → aparece em `get_scheduled_appointments(day)`;
      `cancel` remove; `reschedule` move
- [ ] Teste: `update_lead_qualification` e `create_handoff_task` gravam (inspecionáveis)
- [ ] Commit: `feat(adapters): in-memory FakeCRM implementing CRMPort`

## Tarefa 3.2 — Fichas de tenant (config real)

- [ ] Criar `config/tenants/revenda_veiculos.json` (intents buy/sell_vehicle, 2 serviços
      60min cap.3, seg–sáb, notice 0, lembretes 3x, handoff 4h) e
      `config/tenants/salao_demo.json` (corte 45min cap.2, unha 60min cap.1) — o salão
      é o guardião da agnosticidade (RN-01) desde já
- [ ] Teste: loader (`config/tenant_loader.py`) carrega e valida as duas fichas; ficha com
      intent órfã ou `api_key` literal (não `env:`) → erro claro no BOOT (RN-61, RN-63)
- [ ] Ver falhar → implementar loader (resolve `env:NOME` via settings)
- [ ] Commit: `feat(config): tenant files + validating loader (fail-fast boot)`

## Tarefa 3.3 — Fábrica de adapters

- [ ] Teste: `build_crm(config)` — `type="fake"` → FakeCRM; `type="trivus"` →
      `NotImplementedError` COM mensagem apontando o plano 08; type desconhecido →
      `ValueError` listando os tipos válidos
- [ ] Ver falhar → implementar `adapters/crm/factory.py`
- [ ] Teste RN-03: duas fichas → duas instâncias independentes (criar contato numa não
      aparece na outra)
- [ ] Commit: `feat(adapters): CRM factory keyed by tenant config type (RN-03)`

## Critério de pronto

- [ ] Smoke test integrador: carregar ficha do salão → fábrica → criar contato → calcular
      slots (plano 02) → agendar → listar agenda do dia. Tudo em memória
- [ ] Marcar ✅ no 00-INDEX
