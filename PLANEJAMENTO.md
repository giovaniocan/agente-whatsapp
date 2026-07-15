# PLANEJAMENTO — Agente de IA WhatsApp (multi-tenant)

> **Comece por aqui.** Este é o mapa. O detalhe mora em:
> - [`docs/SPEC.md`](docs/SPEC.md) — fonte da verdade do domínio (regras RN-xx)
> - [`docs/plans/00-INDEX.md`](docs/plans/00-INDEX.md) — os 11 planos em baby steps TDD

## O que é

Agente de IA que atende no WhatsApp em nome de negócios (revenda de veículos, salões
Clube Amore, barbearias…). Conversa em linguagem natural, qualifica lead, agenda, faz
follow-up, escala para humano. **Um motor, vários clientes** — o que muda é a ficha (JSON).

## Princípio de arquitetura (DDD + Hexagonal + Spec-driven + TDD)

O motor não conhece marca nenhuma. Três eixos externos são **plugáveis pela ficha**:

| Eixo | Porta | Adapters | Escolha na ficha |
|------|-------|----------|------------------|
| CRM | `CRMPort` | fake · trivus · clube_amore | `crm.type` |
| Canal WhatsApp | `WhatsAppPort` | zapi · evolution | `channel.type` |
| Cérebro LLM | `LLMPort` | anthropic · openai_compat · gemini | `llm.type` + `llm.model` |

Regra de dependência: `domain` → nada · `application` → só `domain` · `adapters`/`api` →
ambos. Um teste de arquitetura (Plano 01) quebra o build se isso for violado.

## Roadmap por marcos

| Marco | Planos | Resultado observável |
|-------|--------|----------------------|
| **M1** — motor roda | 01 domínio · 02 agenda · 03 fake+fichas · 04 use cases | fluxo completo em teste, sem nada externo |
| **M2** — conversa real | 05 persistência · 06 canal Z-API · 07 cérebro LLM | WhatsApp de teste conversando |
| **M3** — integrado | 08 adapter Trivus | lead/agenda de verdade no trivus-api |
| **M4** — completo | 09 scheduler · 10 RAG | lembretes, auto-resume, conhecimento |
| **M5** — produção | 11 deploy | Coolify, observabilidade, piloto shadow |

## Estado atual

- [x] Domínio inicial: `enums`, `tenant`, `lead`, `crm` (serão retocados no Plano 01)
- [x] SPEC + 11 planos escritos
- [ ] **Plano 01 em execução** (TDD, baby steps)
- [ ] Planos 02–11 pendentes

## Como trabalhamos

TDD obrigatório: teste → vê falhar → implementa o mínimo → vê passar → commit. Um passo
`- [ ]` por vez. Nunca inventar valor real (token, payload) — parar e perguntar.
Rodar sempre no venv: `.venv/bin/python`, `uv run pytest`.
