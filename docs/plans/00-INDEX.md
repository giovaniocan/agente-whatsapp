# Agente WhatsApp — Índice dos Planos de Implementação

> **Leia primeiro.** Define ordem, padrões e como executar. A fonte da verdade do domínio
> é [`../SPEC.md`](../SPEC.md) — os planos citam regras por número (RN-xx).
> Mesmo método do trivus-api: um plano por vez, baby steps, TDD obrigatório.

## Como executar (para a IA/dev)

1. **Um plano por vez, na ordem.** Não pule.
2. Dentro do plano, **um passo (`- [ ]`) por vez**: escreva o teste → rode e VEJA FALHAR →
   implemente o mínimo → rode e veja passar → commit (Conventional Commits).
3. **Não invente.** Faltou um valor real (URL, token, payload)? Pare e pergunte ao humano.
4. Terminou o plano: rode a suíte inteira + ruff + mypy, marque ✅ aqui, e só então avance.
5. Comandos sempre no venv do projeto: `.venv/bin/python`, `uv run pytest`.

## Roadmap

| # | Plano | Entrega observável | Status |
|---|-------|--------------------|--------|
| 01 | [Domínio agnóstico](01-dominio.md) | entidades + ports puros, testados | ✅ |
| 02 | [Agenda (cálculo de slots)](02-agenda.md) | disponibilidade por serviço/capacidade/fuso | ✅ |
| 03 | [FakeCRM + fichas de tenant](03-fake-crm-tenants.md) | fluxo agendamento completo em memória | ✅ |
| 04 | [Use cases de atendimento](04-use-cases-atendimento.md) | qualificar, agendar, escalar (com fakes) | ✅ |
| 05 | [Persistência de conversa](05-persistencia-conversa.md) | Postgres + Alembic + locks + dedupe | ✅ |
| 06 | [Canal Z-API](06-canal-zapi.md) | webhook real: recebe, debounce, responde | ✅ |
| 07 | [Cérebro LLM plugável (tool use)](07-cerebro-llm.md) | conversa natural executando use cases | ⬜ |
| 08 | [Adapter TrivusCRM](08-adapter-trivus.md) | lead/agenda de verdade no trivus-api (staging) | ⬜ |
| 09 | [Scheduler: lembretes/auto-resume](09-scheduler.md) | 3 lembretes + auto-resume + follow-up | ⬜ |
| 10 | [RAG (conhecimento)](10-rag.md) | tool search_knowledge com pgvector | ⬜ |
| 11 | [Produção](11-producao.md) | Docker + CI + Coolify + observabilidade + piloto | ⬜ |

**Marcos:** M1 = planos 01–04 (motor roda com fakes) · M2 = 05–07 (conversa real) ·
M3 = 08 (integrado ao Trivus) · M4 = 09–10 · M5 = 11 (piloto em produção).

## Padrões globais

- **Hexagonal/DDD:** `domain` puro (zero I/O) → `application` (use cases, 1 classe =
  1 caso com `execute()`) → `adapters`/`api` na borda. Dependências apontam para dentro.
- **Teste de arquitetura obrigatório** (plano 01): falha se `domain/` importar de
  `adapters/`, `api/` ou libs de I/O.
- **Nada de vocabulário de ramo/CRM no motor** (RN-01, RN-60) — revisar a cada PR.
- Estrutura de testes espelha `src`: `tests/domain/`, `tests/application/`,
  `tests/adapters/`, `tests/api/`, `tests/e2e/`.
