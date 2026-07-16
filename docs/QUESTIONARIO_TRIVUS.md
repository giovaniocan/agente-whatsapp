# Questionário — integração Agente ↔ trivus-api (Plano 08)

> Para o chat/time do trivus-api. Objetivo: implementar o adapter TrivusCRM
> (8 métodos da CRMPort) sem inventar nenhum campo. **Formato das respostas:
> copy-paste REAL de request + response JSON de cada endpoint (tokens
> redigidos), não descrição em prosa.** Cada exemplo real elimina uma classe
> inteira de bug de tradução.

## 🎯 Atalho (se puder mandar isto, 80% do questionário morre)

1. O arquivo `docs/API_REFERENCE.md` do repo trivus-api (inteiro).
2. O `GET /openapi.json` do staging (o JSON inteiro).
3. URL do staging + credenciais de um usuário de teste numa loja de teste
   (com funil clonado e ao menos 1 SDR ativo) + o `store_id` dessa loja.
4. Um JSON **real e completo** de um lead (response de um GET), com
   agendamento preenchido.

Com isso em mãos, só restam as perguntas marcadas com ⭐ abaixo.

---

## Bloco A — Autenticação e escopo

- **A1.** `POST /auth/login`: request e response reais (campos exatos).
  O token expira em quanto tempo? Existe refresh, ou a estratégia é
  re-login quando vier 401?
- **A2.** ⭐ Usuário de serviço "IA": qual `role`/`shop_role` vocês recomendam
  criar para o agente, e quais permissões mínimas ele precisa para: ler leads,
  criar lead, editar agendamento, ler a agenda e atribuir responsável?
  `menu_permissions` afeta a API ou só o front?
- **A3.** Como o escopo por loja funciona nas rotas: o token já carrega a(s)
  loja(s), ou vai `store_id` em path/query/header? Um exemplo real de chamada
  escopada resolve.
- **A4.** ⭐ Existe gate de assinatura/feature para a integração de IA
  (ecosystem/entitlements)? Se sim: qual `feature_key`, e o corpo exato do
  `403 feature_locked`.

## Bloco B — Leads (contato)

- **B1.** Buscar lead por **telefone**: endpoint + query params exatos.
  A API já trata as variantes do 9º dígito e o `lid` internamente, ou o
  cliente deve mandar as variantes? Response real (é lista? paginada?).
- **B2.** Criar lead: `POST /crm/leads` — payload mínimo aceito + response
  real. ⭐ A API coloca o lead na 1ª etapa do funil clonado e faz o
  round-robin de SDR automaticamente (como o webhook antigo fazia), ou o
  chamador precisa mandar `stage_id`/`assigned_to`?
- **B3.** ⭐ Dedupe: se eu criar um lead com telefone que já existe na loja,
  a API recusa (409?), devolve o existente, ou duplica?
- **B4.** Atualizar qualificação: endpoint + payload real. Quais campos o
  agente pode escrever: `qualificado`, `urgencia_venda`, `observacoes`,
  `origem_mkt`? Algum é bloqueado por papel?

## Bloco C — Agenda / agendamento

- **C1.** `PATCH /crm/leads/{id}/agendamento`: payload exato (formato de
  `data_agendamento` e `hora_agendamento`) + response. O back seta sozinho
  `agendado_por` e `data_marcacao_agendamento`?
- **C2.** Cancelar agendamento: é o mesmo endpoint com `null`s? Exemplo real.
- **C3.** Reagendar: mesmo endpoint com valores novos? Alguma regra especial
  (recalcula `data_marcacao_agendamento`? grava histórico?).
- **C4.** `GET /agenda`: parâmetros para filtrar UM dia (nomes exatos:
  `dateFrom`/`dateTo`? `periodApplyTo`?), como funciona a paginação
  (25/50/100) — preciso de TODOS os agendamentos do dia —, e o response real
  de um item.
- **C5.** ⭐ Confirmação de fuso: datas/horas são naïve em horário de
  Brasília em TODA a API? Existe hoje (ou está previsto) loja com fuso
  diferente?

## Bloco D — Handoff (atribuir a humano + contexto)

- **D1.** Atribuir lead a um humano: `PATCH /crm/leads/{id}` aceita
  `assigned_to`/`vendedor_id`? Payload real.
- **D2.** Como listo o time da loja para escolher o destinatário
  (ex.: `GET /stores/{id}/team`)? Response real.
- **D3.** ⭐ Existe endpoint para registrar atividade/nota no lead
  (`crm_activity_log` é exposto?)? Se não, gravar o contexto do handoff em
  `observacoes` é aceitável? O PATCH de observações faz APPEND ou SOBRESCREVE?

## Bloco E — Operacional

- **E1.** URL do staging + como obtenho credenciais. Existe loja de teste com
  funil clonado + SDRs? Qual o `store_id`?
- **E2.** A API tem rate limit? Qual?
- **E3.** ⭐ O AGENTE vai ser a porta de entrada do WhatsApp e criar o lead
  via API (decisão registrada). Para a loja piloto, como garantimos que o
  webhook zapi do PRÓPRIO trivus-api fica desligado (`zapi_webhook_enabled=false`?)
  — senão o lead entra em dobro.
- **E4.** Catálogo de erros: um exemplo real do corpo de cada um
  (400, 401, 403, 404, 422).

---

### O que já está decidido do nosso lado (contexto p/ quem responder)

- O agente consome a API REST com JWT de um usuário de serviço por loja.
- Disponibilidade é calculada NO agente (a API só informa os agendados do dia).
- Handoff = atribuir o lead + registrar contexto (D3 define onde).
- O adapter valida toda resposta com Pydantic e traduz datas naïve-Brasília ↔
  tz-aware internamente; nomes do Trivus não vazam para fora do adapter.
