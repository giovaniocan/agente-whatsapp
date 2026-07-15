# Plano 06 — Canal WhatsApp (Z-API primeiro; canal plugável)

**Objetivo:** o agente vira a porta de entrada real do WhatsApp do tenant (RN-40):
recebe webhook, filtra, agrupa (debounce), processa em background e responde.
**Regras cobertas:** RN-40, RN-40b, RN-41…RN-45, RN-22.

> **RN-40b:** o canal é escolhido pela ficha (`channel.type`). Neste plano implementamos
> SÓ o Z-API (tenant Trivus, custo repassado). O Evolution (opção Clube Amore,
> self-hosted) é um adapter futuro — a fábrica de canal já nasce aqui para o encaixe
> ficar pronto, mas `type="evolution"` → `NotImplementedError` apontando este plano.

## Tarefa 6.0 — Fábrica de canal (RN-40b)

- [ ] Teste: `build_channel(config)` — `"zapi"` → ZapiWhatsApp; `"evolution"` →
      `NotImplementedError` com mensagem clara; desconhecido → `ValueError`
- [ ] Ver falhar → implementar `adapters/whatsapp/factory.py` (espelho da fábrica de CRM)
- [ ] Ficha ganha bloco `channel` validado pelo loader (plano 03)
- [ ] Commit: `feat(adapters): channel factory keyed by tenant config (RN-40b)`

## Tarefa 6.1 — Parser do payload Z-API

- [ ] Coletar payloads REAIS (do Trivus atual / docs Z-API) como fixtures JSON —
      texto, grupo, fromMe, newsletter, lid-sem-telefone. **Não inventar payload**
- [ ] Teste: parser extrai phone normalizado (sem DDI 55) e lid; aplica filtros RN-41 →
      resultado `Ignored(reason)` ou `IncomingMessage(phone, lid, text, message_id)`
- [ ] Ver falhar → implementar `adapters/whatsapp/zapi_parser.py` (portar regras de
      `extractLeadIdentity`/variantes do Trivus, reusar `utils/phone.py`)
- [ ] Commit: `feat(adapters): Z-API payload parser with entry filters (RN-41)`

## Tarefa 6.2 — Envio (WhatsAppPort)

- [ ] `uv add httpx respx --group dev`
- [ ] Teste (respx): `ZapiWhatsApp.send_text` faz POST correto com token do tenant;
      5xx → retry com backoff (máx 3); erro final → exceção clara
- [ ] Ver falhar → implementar `adapters/whatsapp/zapi.py` (httpx.AsyncClient, RN-65)
- [ ] Commit: `feat(adapters): Z-API sender implementing WhatsAppPort`

## Tarefa 6.3 — Webhook FastAPI (RN-45, RN-42)

- [ ] Teste (httpx ASGI): `POST /webhook/whatsapp/{tenant_token}` — token desconhecido →
      401; payload de grupo → 200 `{skipped}`; mensagem válida → 200 IMEDIATO e
      processamento agendado em background
- [ ] Ver falhar → implementar `api/webhook.py` (BackgroundTasks/task queue interna)
- [ ] Teste: mesmo `message_id` duas vezes → segunda ignorada (dedupe do plano 05)
- [ ] Commit: `feat(api): whatsapp webhook, 200-first + background processing`

## Tarefa 6.3b — Armazenar histórico de mensagens (base do buffer, RN-74/75)

- [ ] Migration: tabela `messages` (id, conversation_id FK, direction in/out, text,
      provider_message_id, created_at) — o histórico que o summarization buffer consome
- [ ] Teste: store grava mensagem in/out; `recent_messages(conversation, n)` devolve as
      últimas N em ordem; dedupe por provider_message_id continua (RN-42)
- [ ] Ver falhar → implementar no PostgresConversationStore
- [ ] Commit: `feat(store): message history for summarization buffer (RN-74)`

## Tarefa 6.4 — Debounce (RN-43) e lock (RN-44)

- [ ] Teste: 3 mensagens do mesmo phone em 2s → UMA chamada ao ProcessIncomingMessage
      com o texto agrupado; janela configurável (default 6s); relógio injetado
- [ ] Ver falhar → implementar buffer por conversa (asyncio, ou tabela jobs com run_at)
- [ ] Teste: processamento roda DENTRO do lock da conversa
- [ ] Commit: `feat(app): per-conversation debounce buffer and locked processing`

## Critério de pronto (com 07 fecha M2)

- [ ] Manual: número de teste + FakeCRM + resposta "eco" → mensagem no WhatsApp real
      entra e sai. Documentar setup em `docs/DEV_SETUP.md`
- [ ] Marcar ✅ no 00-INDEX
