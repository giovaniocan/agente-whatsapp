# Pendências — coisas que dependem de você (Giovani)

> Itens que EU não consigo resolver sozinho: credenciais, acessos, confirmações
> de payload real e decisões de negócio. Organizado por quando é necessário.
> Nada aqui bloqueia o desenvolvimento com mocks/fixtures — bloqueia só a
> validação REAL de cada parte.

## 🔴 Antes do go-live do canal WhatsApp (Plano 06)

- [ ] **Payload real do Z-API** — me mandar um exemplo real de mensagem recebida
      da sua instância. Preciso confirmar os campos `text.message` e `messageId`
      (os de identidade — phone/chatLid/isGroup/fromMe — já espelham o Trivus).
      Onde afeta: `adapters/whatsapp/zapi_parser.py`.
- [ ] **Credenciais da instância Z-API** (via env, nunca no código):
      `ZAPI_INSTANCE_ID`, `ZAPI_TOKEN` e, se sua conta usar, `ZAPI_CLIENT_TOKEN`.
      Onde afeta: envio real (`ZapiWhatsApp`) e o teste ponta-a-ponta.
- [ ] **Número de teste** dedicado para o piloto (não o número principal da loja).
- [ ] Decidir o webhook: confirmar que o Z-API vai apontar "ao receber" para
      `POST /webhook/whatsapp/{tenant_token}` do agente (RN-40).

## 🔴 Antes de ligar o cérebro (Plano 07)

- [ ] **`ANTHROPIC_API_KEY`** (via env) para a validação real do LLM. Os adapters
      são construídos e testados com SDK mockada — a chave só é necessária para
      conversar de verdade.
- [ ] Confirmar modelo por tenant na ficha: default `claude-sonnet-5` (principal)
      + `claude-haiku-4-5` (resumo barato, RN-75). Trocar se preferir.

## 🟡 Integração com o Trivus (Plano 08)

- [ ] **Acesso ao repo `trivusauto/trivus-api`** — preciso do `docs/API_REFERENCE.md`
      e do `/openapi.json` (staging) para copiar payloads REAIS (proibido inventar).
- [ ] **Usuário de serviço "IA" por loja** no trivus-api (JWT), + credenciais via env
      (`TRIVUS_TOKEN_<LOJA>`). Confirmar se há endpoint machine-to-machine melhor.
- [ ] **Ambiente de staging** do trivus-api para o smoke test (criar/agendar/cancelar
      um lead de teste e ver no Trivus).

## 🟡 RAG / base de conhecimento (Plano 10)

- [ ] Decidir **provedor de embeddings** (Voyage, OpenAI, ou local) — impacta custo.
- [ ] Fonte do conhecimento do 1º cliente: FAQ, políticas, estoque (formato e de onde
      vem — planilha? site? export do Trivus?).

## 🟡 Produção (Plano 11)

- [ ] **Coolify**: projeto + Postgres gerenciado + secrets (todas as envs acima).
- [ ] Definir com o cliente os **critérios de saída do shadow mode** (quando a IA
      passa de "sugere" para "autônoma"): taxa de acerto, zero violações da RN-30,
      agendamentos válidos.
- [ ] Rotacionar segredos antigos expostos (nota de segurança do PDF do Trivus).

## 🟢 Decisões de produto (quando quiser)

- [ ] Fichas reais dos primeiros tenants (revenda + Clube Amore): persona, horários,
      serviços/durações/capacidade, mensagens de handoff, janelas de follow-up.
- [ ] Canal por tenant: Trivus/revenda = Z-API; Clube Amore = Z-API ou Evolution
      (self-hosted). Só um campo na ficha (RN-40b).

---

### Já resolvido / não bloqueia
- Postgres de dev: `docker compose up -d` (porta 5439). ✅
- Arquitetura, domínio, agenda, use cases, persistência: prontos e testados. ✅
- Estratégia de custo de token (caching/summary/budget): no contrato (RN-74..79). ✅

## 🆕 Sessão planos 09/10/11 (15/07/2026)

- [ ] **Executar o deploy no Coolify** — infra pronta (`Dockerfile`, `ci.yml`,
      `docs/DEPLOY.md`); faltam os acessos/secrets. Banco DEVE ser imagem
      `pgvector/pgvector:pg16`.
- [ ] **Provedor de embeddings definitivo** (OpenAI vs Voyage). Hoje: OpenAI se
      `OPENAI_API_KEY` existir, senão FakeEmbedder (só dev). Ao decidir, fixar a
      dimensão do vetor e criar índice ivfflat (migration).
- [ ] **Fiação do circuit breaker** nos adapters Z-API/CRM (utilitário pronto e
      testado em `utils/circuit_breaker.py`).
- [ ] Follow-up multiestágio (hoje: 1 disparo por resposta, configurável na
      ficha) — só se o negócio pedir.
- [ ] Push do repo p/ GitHub para o CI (`.github/workflows/ci.yml`) rodar.
