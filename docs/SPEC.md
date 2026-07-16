# SPEC — Agente de IA para WhatsApp (multi-tenant, agnóstico a CRM)

> **Fonte da verdade do domínio.** Os planos em `plans/` referenciam esta spec por número de regra (RN-xx).
> Quando código e spec divergirem, a spec vence — ou a spec é corrigida ANTES do código.
> Padrão herdado do trivus-api: spec-driven + DDD + hexagonal + TDD.

---

## 1. O que é o sistema

Agente de IA que atende no WhatsApp em nome de negócios (tenants): conversa em linguagem
natural, qualifica o lead, agenda atendimentos, faz follow-up e escala para humano.
Um **único motor** serve todos os tenants; o que muda por tenant é a **ficha de configuração**.

**Tenants conhecidos:**

| Tenant | Ramo | Sistema por trás | `crm.type` |
|---|---|---|---|
| Revenda de veículos | compra/venda de carros | trivus-api (REST, pronto) | `trivus` |
| Clube Amore | salões femininos (cabelo, unhas…) | app próprio de agendamento | `clube_amore` (futuro) |
| Demo/testes | qualquer | memória | `fake` |

## 2. Linguagem ubíqua (DDD)

| Termo | Significado | NÃO confundir com |
|---|---|---|
| **Tenant** | O negócio cliente do agente (uma revenda, um salão). Dono de uma ficha | loja do Trivus (é o conceito espelho lá) |
| **Ficha (tenant config)** | JSON validado que declara persona, serviços, agenda, CRM do tenant | settings do app (env) |
| **Contact** | Pessoa já gravada no CRM do tenant | LeadInfo |
| **LeadInfo** | Rascunho do lead construído durante a conversa (em memória) | Contact |
| **Conversation** | Estado de um papo com um telefone: histórico, handoff, lead em construção | sessão HTTP |
| **Service** | Item agendável do tenant (ex.: "vender veículo 60min", "corte 45min") | serviço do catálogo Trivus (upsell) |
| **Intent** | O que a pessoa quer, dentre as intents declaradas na ficha | enum fixo (não existe mais) |
| **Slot** | Janela de horário candidata a agendamento, calculada pelo agente | agenda do CRM |
| **Appointment** | Agendamento confirmado no CRM | Slot |
| **Handoff** | Transferência da conversa para um humano | fim da conversa |
| **HandoffTask** | Pacote de contexto entregue ao CRM/time no handoff | tarefa genérica |

## 3. Bounded contexts (mapa de contextos)

```
┌─ Atendimento ─────────────┐   ┌─ Agenda ────────────────┐
│ Conversation, LeadInfo,   │   │ Slot, SchedulingPolicy, │
│ Handoff, debounce, locks  │──▶│ Appointment (cálculo)   │
└───────────┬───────────────┘   └───────────┬─────────────┘
            │ usa ports                     │ usa ports
            ▼                               ▼
┌─ Integração CRM (ACL) ────────────────────────────────────┐
│ CRMPort ← FakeCRM | TrivusCRM | ClubeAmoreCRM (futuro)    │
│ ÚNICO lugar onde vocabulário externo existe               │
└───────────────────────────────────────────────────────────┘
┌─ Conhecimento (RAG) ──────┐   ┌─ Notificações ──────────┐
│ KnowledgePort, pgvector   │   │ lembretes, follow-up,   │
└───────────────────────────┘   │ auto-resume (scheduler) │
                                └─────────────────────────┘
```

## 4. Regras de negócio (RN-xx)

### Núcleo agnóstico

- **RN-01 — Motor único, ficha por tenant.** Nenhum use case, prompt-base, tabela ou
  entidade do agente menciona ramo ("veículo") ou sistema ("Trivus"). Vocabulário
  específico entra SÓ pela ficha do tenant e pelos adapters.
- **RN-02 — Intents declaradas na ficha.** Cada tenant declara suas intents válidas
  (revenda: `buy_vehicle`, `sell_vehicle`; salão: `haircut`, `nails`, …). O domínio trata
  intent como `str` validada contra a ficha, nunca enum fixo.
- **RN-03 — Isolamento por construção.** Cada instância de adapter nasce amarrada a um
  tenant (recebe o `CRMConfig` no construtor). Métodos da porta NÃO recebem `tenant_id`.

### Agenda

- **RN-10 — Disponibilidade é calculada no agente.** Slots livres = grade das
  `working_hours` do tenant − agendamentos ocupados (`get_scheduled_appointments`),
  no fuso do tenant. O CRM só informa o que está ocupado.
- **RN-11 — Duração e capacidade por SERVIÇO.** Cada `Service` tem `duration_minutes` e
  `capacity` próprios (salão: 2 cortes simultâneos, 1 manicure). A `SchedulingPolicy`
  global fornece defaults. Revenda: 60 min, capacidade 3, para ambos os serviços. Com `scheduling.shared_capacity: true`, a ocupação vale
  para a LOJA inteira (toda intent conta) — caso revenda/CRMs que não registram o serviço.
- **RN-12 — Antecedência mínima configurável.** `min_notice_minutes` na ficha (revenda: 0).
- **RN-13 — Revalidação no commit.** `ScheduleAppointment` revalida o slot contra a
  disponibilidade no momento de gravar (duas conversas podem disputar a última vaga).
  Falhou a revalidação → oferece outro horário, nunca sobrescreve.
- **RN-14 — Datas tz-aware no domínio.** Todo `datetime` do domínio carrega timezone
  (o do tenant, default `America/Sao_Paulo`). Datas naïve são erro de fronteira.

### Lead e qualificação

- **RN-20 — Dados obrigatórios para agendar** (ficha da revenda): nome completo, telefone,
  intent, data e horário. Opcionais: modelo/cor do veículo, e-mail, observações.
  A ficha de cada tenant pode declarar o próprio conjunto de campos extras.
- **RN-21 — Qualificação atualizada no CRM.** O agente classifica intent, urgência e
  prioridade e grava via `update_lead_qualification`. Lead qualificado é roteado ao time
  de vendas (no Trivus: `assigned_to`/round-robin já existente).
- **RN-22 — Identidade por telefone com variantes.** Busca de contato considera as
  variantes brasileiras do 9º dígito e, quando houver, o `lid` do WhatsApp.

### Fronteira humana e handoff

- **RN-30 — Fronteira humana POR DESIGN.** O agente NUNCA: concede desconto, negocia ou
  define preço, fecha contrato, trata financiamento, lida com reclamação crítica.
  Implementação: essas ferramentas **não existem** no tool-set do LLM.
- **RN-31 — Fluxo de handoff, nesta ordem:** (1) `handoff_status=PENDING` — a IA para de
  responder imediatamente; (2) monta pacote de contexto (histórico + lead + motivo +
  routing hint); (3) `create_handoff_task` no CRM; (4) notifica o time (WhatsApp interno);
  (5) envia mensagem de handoff ao cliente; (6) **auto-resume**: sem resposta humana em
  X horas (ficha), a IA retoma (`ACTIVE`).
- **RN-32 — Gatilhos de escalada:** pedido explícito, insatisfação, confusão persistente,
  pedido fora das regras (RN-30), risco de perda do cliente.

### Canal WhatsApp (plugável por tenant)

- **RN-40 — O agente é a porta de entrada do webhook** do gateway do tenant. Criar/
  enriquecer o lead no CRM é responsabilidade do ADAPTER de CRM, não do motor.
- **RN-40b — Canal é escolha da FICHA, como o CRM.** `channel.type` declara o gateway:
  `zapi` (SaaS pago — Trivus/revendas, custo repassado ao cliente) ou `evolution`
  (self-hosted, sem licença — opção para Clube Amore absorver a operação). O motor só
  conhece a `WhatsAppPort`; cada gateway tem adapter + parser próprios que produzem o
  mesmo `IncomingMessage`. Ambos são APIs não-oficiais — risco operacional equivalente;
  a escolha é comercial, não técnica.
- **RN-41 — Filtros de entrada:** ignorar grupos, `fromMe`, newsletters (mesmas regras do
  Trivus hoje) — aplicados no parser de CADA gateway.
- **RN-42 — Idempotência:** dedupe pelo id de mensagem do gateway; webhook pode reentregar.
- **RN-43 — Debounce:** agrupar mensagens da mesma pessoa por ~5–8s antes de chamar o LLM.
- **RN-44 — Lock por conversa:** nunca processar duas mensagens do mesmo telefone em
  paralelo (advisory lock por `conversation_id`).
- **RN-45 — Webhook responde 200 imediato** e processa em background (gateways têm timeout).

### Cérebro (LLM plugável)

- **RN-70 — O LLM é escolha da FICHA, como CRM e canal.** `llm.type` declara o provedor
  (`anthropic`, `openai_compat`, `gemini`, …) e `llm.model` o modelo. O motor só conhece
  a `LLMPort`; trocar/fluir entre IAs = trocar a ficha, zero mudança no motor.
- **RN-71 — Dialeto neutro de tools (ACL do LLM).** O domínio define `ToolSpec`,
  `ToolCall(name, args)` e `Reply(text)` próprios. CADA adapter traduz de/para o formato
  de function calling do provedor (tool_use da Anthropic, function_call da OpenAI, …).
  Nenhum formato de provedor vaza para application/domain.
- **RN-72 — `openai_compat` é um adapter só** com `base_url` configurável — cobre OpenAI,
  Groq, DeepSeek, Ollama local e qualquer API compatível, sem código novo por provedor.
- **RN-73 — Requisito mínimo de provedor:** suportar function calling confiável. A RN-30
  (fronteira humana) e a RN-02 (intents da ficha) valem para QUALQUER provedor — os testes
  do tool-set rodam contra o formato neutro, não contra um provedor.

### Cérebro — economia de tokens e segurança

- **RN-74 — NUNCA enviar o histórico inteiro.** O contexto enviado ao LLM é sempre:
  `system prompt (cacheável)` + `resumo rolante` + `últimas N mensagens verbatim` +
  `mensagem atual`. N é configurável por tenant (`llm.recent_window`, default 10).
  O adapter monta isso; o motor entrega a `Conversation` (que já carrega `summary`).
- **RN-75 — Summarization buffer.** Quando o histórico passa de um limiar, as mensagens
  mais antigas são resumidas para `Conversation.summary` por um modelo BARATO
  (`llm.summary_model`, ex. Haiku) e descartadas do envio verbatim. Resumir é escrita
  incremental (resumo + novas antigas → novo resumo), não do zero toda vez.
- **RN-76 — Prompt caching é obrigatório quando o provedor suporta.** O prefixo estável
  por tenant (system prompt + tools + few-shot) é marcado como cacheável (ex. `cache_control`
  da Anthropic). Isso permite prefixo rico (few-shot/regras) SEM pagar por ele a cada
  mensagem — a alavanca nº 1 de custo. Ordem do payload: estável primeiro, dinâmico depois.
- **RN-77 — Extração estruturada, não parsing de texto.** Capturar dados do lead
  (nome, intent, veículo, etc.) usa saída estruturada (tool/JSON schema) validada por
  Pydantic na fronteira (RN-61). Nunca extrair via regex/heurística sobre texto livre.
- **RN-78 — Defesa contra prompt injection (defesa em profundidade).** (1) Todo texto do
  WhatsApp é NÃO CONFIÁVEL; o system prompt instrui a ignorar instruções embutidas na
  mensagem do usuário que tentem alterar regras/persona. (2) A defesa real é a RN-30: como
  ações proibidas (desconto/preço/contrato) não existem como ferramenta, uma injeção
  bem-sucedida não consegue executá-las. Prompt é a 1ª linha; a ausência de ferramenta é a
  garantia.
- **RN-79 — Rastreamento de budget de tokens.** Cada requisição registra tokens de entrada,
  de entrada CACHEADOS, de saída e custo estimado, por conversa e por tenant. Métrica
  exposta desde o dia 1 (base para achar os 20–30% otimizáveis).

### Lembretes e follow-up

- **RN-50 — Lembretes de agendamento: 3 disparos** — 1 dia antes, manhã do dia, 1 hora
  antes — no fuso do tenant. Cancelou/reagendou → lembretes recalculados.
- **RN-51 — Follow-up de lead frio** conforme regra da ficha (configurável por tenant).

### Integração (ACL) e qualidade

- **RN-60 — Zero vazamento de vocabulário.** Nomes/conceitos de sistema externo
  (ex.: `crm_funnel_leads`, `data_agendamento`) só existem dentro do adapter respectivo.
- **RN-61 — Validar na fronteira, falhar cedo.** Toda resposta externa é validada com
  Pydantic no adapter; payload inesperado → erro claro, nunca dado torto adiante.
- **RN-62 — Tradução de tempo no adapter Trivus:** trivus-api usa data `YYYY-MM-DD` +
  hora `"HH:MM:SS"` naïve em horário de Brasília; o adapter converte de/para os
  datetimes tz-aware do domínio (RN-14).
- **RN-63 — Segredos só por env** (pydantic-settings). Ficha de tenant commitada nunca
  contém `api_key`/senha — contém a REFERÊNCIA da env (ex.: `env:TRIVUS_TOKEN_LOJA_X`).
- **RN-64 — Auth no trivus-api:** usuário de serviço "IA" por loja (JWT Bearer);
  renovar token no 401. `403 feature_locked` → erro claro de plano, não retry.
- **RN-65 — Toda chamada de rede é async** (httpx.AsyncClient); timeouts e retry
  explícitos; sem I/O no domínio.
- **RN-66 — Código e nomes em inglês; comentários podem ser em PT-BR.**

## 5. Convenções técnicas

| Item | Decisão |
|---|---|
| Python | 3.11+ (venv do projeto via uv) |
| Framework | FastAPI async |
| Validação | Pydantic v2 em toda fronteira |
| Persistência do agente | PostgreSQL + SQLAlchemy 2 async + Alembic (banco PRÓPRIO, não o do Trivus) |
| LLM | plugável por tenant (RN-70): anthropic · openai_compat · gemini · … |
| Canal | plugável por tenant (RN-40b): Z-API (Trivus) · Evolution (opção Clube Amore) |
| Qualidade | pytest + pytest-asyncio; ruff; mypy; TDD obrigatório |
| Layout | `src/agente/{domain,application,adapters,api,config,utils}` |
| Regra de dependência | `domain` não importa de ninguém; `application` importa só de `domain`; `adapters`/`api` importam de ambos |

## 6. Portas (contratos do domínio)

Assinaturas completas nos planos; resumo:

- **CRMPort** — `find_contact_by_phone`, `create_contact`, `update_lead_qualification`,
  `get_scheduled_appointments(day)`, `create_appointment`, `cancel_appointment`,
  `reschedule_appointment`, `create_handoff_task`
- **WhatsAppPort** — `send_text(phone, text)` (mídia depois)
- **LLMPort** — `respond(conversation, tools: list[ToolSpec]) -> Reply | ToolCall`
  (tipos neutros do domínio, RN-71; adapters traduzem para o dialeto do provedor)
- **ConversationStorePort** — carregar/salvar `Conversation`, dedupe de mensagem, lock
- **KnowledgePort** — `search(tenant, query, k) -> chunks`
- **SchedulerPort** — agendar/cancelar jobs (lembretes, auto-resume, follow-up)

## 7. Ficha do tenant (schema resumido)

```jsonc
{
  "id": "revenda_x",
  "name": "Revenda X",
  "persona": { "name": "Ana", "tone": "cordial e objetivo", "language": "pt-BR" },
  "intents": ["buy_vehicle", "sell_vehicle"],          // RN-02
  "services": [
    { "name": "Comprar veículo", "intent": "buy_vehicle",
      "duration_minutes": 60, "capacity": 3 }           // RN-11
  ],
  "scheduling": {
    "timezone": "America/Sao_Paulo",
    "min_notice_minutes": 0,                             // RN-12
    "working_hours": [ { "weekday": 0, "open": "09:00", "close": "18:00" } ]
  },
  "handoff": { "auto_resume_hours": 4, "team_phone": "..." },   // RN-31
  "reminders": ["P1D", "morning", "PT1H"],               // RN-50
  "channel": { "type": "zapi",                           // RN-40b: "zapi" | "evolution"
               "api_key": "env:ZAPI_TOKEN_REVENDA_X" },  // salão poderia usar "evolution"
  "llm": { "type": "anthropic",                          // RN-70: "anthropic" | "openai_compat" | "gemini"
           "model": "claude-sonnet-5",                   // modelo principal
           "summary_model": "claude-haiku-4-5",          // RN-75: modelo barato p/ resumir
           "recent_window": 10,                          // RN-74: últimas N msgs verbatim
           "prompt_cache": true,                         // RN-76: cachear prefixo estável
           "api_key": "env:ANTHROPIC_API_KEY" },         // openai_compat aceita "base_url" (Groq/Ollama/…)
  "crm": { "type": "trivus", "base_url": "https://...",
           "api_key": "env:TRIVUS_TOKEN_REVENDA_X",      // RN-63
           "settings": { "store_id": "uuid-da-loja" } }
}
```
