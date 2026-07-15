# Plano 10 — RAG: base de conhecimento por tenant

**Objetivo:** o agente responde dúvidas do negócio (políticas, FAQ, estoque) buscando na
base do tenant, via tool `search_knowledge`.
**Regras cobertas:** RN-01 (conteúdo vem da base do tenant, nunca do prompt), RN-63.

## Tarefa 10.1 — Schema e port

- [ ] Migration: extensão pgvector + tabela `knowledge_chunks`
      (tenant_id, source, content, embedding vector, metadata jsonb) + índice ivfflat
- [ ] Teste: `KnowledgePort.search(tenant_id, query, k)` — isolamento entre tenants
      (chunk do salão NUNCA volta para a revenda; teste explícito)
- [ ] Commit: `feat(rag): pgvector schema with hard tenant isolation`

## Tarefa 10.2 — Embeddings e ingestão

- [ ] Decidir com o humano o provedor de embeddings (voyage/openai) e registrar aqui
- [ ] Teste (API mockada): `ingest(tenant_id, documents)` → chunking (~500 tokens,
      overlap), embeddings, upsert idempotente por hash do conteúdo
- [ ] Ver falhar → implementar `adapters/vectorstore/pgvector.py` + CLI
      `python -m agente.ingest <tenant> <arquivo.md>`
- [ ] Commit: `feat(rag): chunking + idempotent ingestion CLI`

## Tarefa 10.3 — Tool no cérebro

- [ ] Teste: tool `search_knowledge` adicionada ao tool-set (plano 07); pergunta de FAQ →
      LLM chama a tool → chunks entram como tool_result → resposta cita a base
- [ ] Teste: base vazia → LLM instruído a dizer que vai confirmar com o time
      (nunca inventar preço/condição — reforço da RN-30)
- [ ] Ver falhar → implementar
- [ ] Commit: `feat(rag): search_knowledge tool wired into the brain`

## Critério de pronto

- [ ] Ingerir FAQ real do 1º cliente e validar 5 perguntas manualmente
- [ ] Marcar ✅ no 00-INDEX
