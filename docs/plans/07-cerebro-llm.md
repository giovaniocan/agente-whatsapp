# Plano 07 — Cérebro: LLM plugável (tool use agnóstico a provedor)

**Objetivo:** substituir o eco por um LLM decidindo entre responder e chamar use cases —
com o provedor escolhido pela FICHA (anthropic, openai_compat, gemini…), não pelo código.
**Regras cobertas:** RN-01 (prompt), RN-02, RN-30, RN-70…RN-73.

> Mesmo esquema de CRM e canal: `LLMPort` + adapters + fábrica. O que cruza a porta são
> tipos NEUTROS do domínio (`ToolSpec`, `ToolCall`, `Reply`) — cada adapter traduz para o
> dialeto de function calling do provedor dele (RN-71).

## Tarefa 7.1 — Tipos neutros da porta (RN-71)

- [ ] Teste: `ToolSpec(name, description, parameters: dict)` (JSON Schema),
      `ToolCall(name, args)`, `Reply(text)` — roundtrip de serialização
- [ ] Ver falhar → implementar em `domain/llm.py`; `LLMPort.respond(conversation,
      system_prompt, tools) -> Reply | ToolCall` atualizada em `ports.py`
- [ ] Commit: `feat(domain): neutral LLM types (ToolSpec/ToolCall/Reply) (RN-71)`

## Tarefa 7.2 — Definição das tools (contrato use cases ↔ LLM)

- [ ] Teste: `build_tools(tenant)` gera `list[ToolSpec]` com `get_availability`,
      `schedule_appointment`, `reschedule_appointment`, `cancel_appointment`,
      `qualify_lead`, `escalate_to_human` — intents da ficha como enum no schema (RN-02),
      datas ISO. **Formato neutro** — nenhuma menção a provedor
- [ ] Teste RN-30/RN-73: a lista NUNCA contém preço/desconto/financiamento (asserção
      literal, roda contra o formato neutro — vale para qualquer provedor)
- [ ] Ver falhar → implementar `application/tools.py` (repare: application, não adapter —
      o contrato das tools é do MOTOR)
- [ ] Commit: `feat(app): tenant-scoped neutral tool specs (RN-02, RN-30)`

## Tarefa 7.3 — System prompt da ficha (RN-01)

- [ ] Teste: `build_system_prompt(tenant)` contém persona, serviços, horários, regras de
      escalada (RN-32) e "nunca negocie valores; escale" — sem nada hardcoded de ramo
      (rodar com ficha do salão E da revenda)
- [ ] Ver falhar → implementar template em `application/prompt.py`
- [ ] Commit: `feat(app): system prompt rendered from tenant config only`

## Tarefa 7.4 — Adapter Anthropic (1º provedor)

- [ ] `uv add anthropic`; ficha: `llm.type="anthropic"`, `llm.model`, `api_key: env:` (RN-63)
- [ ] Teste (SDK mockada): tradução IDA — `list[ToolSpec]` → formato `tools` da Anthropic;
      VOLTA — resposta `tool_use` → `ToolCall`; resposta texto → `Reply`; erro de API →
      exceção própria com retry
- [ ] Ver falhar → implementar `adapters/llm/anthropic_llm.py` (histórico com janela +
      resumo persistido em `conversations.summary` p/ controle de custo)
- [ ] Commit: `feat(llm): Anthropic adapter translating neutral tool dialect`

## Tarefa 7.5 — Adapter OpenAI-compatible (RN-72)

- [ ] `uv add openai`; aceita `base_url` na ficha → cobre OpenAI, Groq, DeepSeek,
      Ollama local etc. sem código novo
- [ ] Teste (mock): mesma bateria da 7.4 no dialeto `function_call`/`tools` da OpenAI
- [ ] Ver falhar → implementar `adapters/llm/openai_compat_llm.py`
- [ ] Commit: `feat(llm): OpenAI-compatible adapter (one adapter, many providers) (RN-72)`

## Tarefa 7.6 — Fábrica de LLM (RN-70)

- [ ] Teste: `build_llm(config)` — `anthropic` → AnthropicLLM; `openai_compat` →
      OpenAICompatLLM; `gemini` → `NotImplementedError` apontando este plano;
      desconhecido → `ValueError` listando válidos
- [ ] Teste de CONTRATO compartilhado: a MESMA suíte (responder texto, chamar tool,
      erro de API) roda parametrizada contra todos os adapters registrados — garante
      que trocar de provedor não muda comportamento observável
- [ ] Ver falhar → implementar `adapters/llm/factory.py`; loader da ficha valida bloco `llm`
- [ ] Commit: `feat(llm): provider factory + shared contract test suite (RN-70)`

## Tarefa 7.7 — Fechamento do loop no ProcessIncomingMessage

- [ ] Teste integração (LLM fake): `ToolCall` de agendamento → use case executado →
      resultado volta ao LLM → `Reply` final enviada; `SlotTakenError` → LLM recebe
      alternativas e reformula (RN-13 conversacional)
- [ ] Teste: `MissingLeadDataError` → LLM recebe os campos faltantes e pergunta (RN-20)
- [ ] Ver falhar → implementar
- [ ] Commit: `feat(app): full tool-execution loop with graceful error surfacing`

## Critério de pronto (fecha M2)

- [ ] Conversa manual real no WhatsApp de teste com o provedor escolhido na ficha
      (qualificação + agendamento + escalada, FakeCRM); transcript em `docs/exemplos/`
- [ ] Trocar `llm.type` na ficha e repetir 3 mensagens — funciona sem tocar código
- [ ] Tokens/custo por conversa logados desde já
- [ ] Marcar ✅ no 00-INDEX
