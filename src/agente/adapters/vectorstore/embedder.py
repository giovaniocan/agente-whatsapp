"""
Embedders (EmbeddingPort) — plano 10.

- FakeEmbedder: bag-of-words com hashing, determinístico e normalizado. Serve
  para testes e para rodar RAG sem provedor pago (similaridade por sobreposição
  de palavras).
- OpenAIEmbedder: provedor real via API compatível com OpenAI. O provedor
  definitivo (OpenAI vs Voyage) é decisão pendente do humano — trocar é
  registrar outro adapter.
"""

import hashlib
import math
from typing import Any


class FakeEmbedder:
    def __init__(self, dim: int = 32) -> None:
        self._dim = dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        for word in text.lower().split():
            digest = hashlib.sha256(word.encode()).digest()
            bucket = int.from_bytes(digest[:4], "big") % self._dim
            vec[bucket] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


class OpenAIEmbedder:
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str = "",
        base_url: str = "",
        client: Any | None = None,
    ) -> None:
        self._model = model
        if client is None:  # pragma: no cover - construção real
            import openai

            client = openai.AsyncOpenAI(api_key=api_key or None, base_url=base_url or None)
        self._client: Any = client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(model=self._model, input=texts)
        return [list(item.embedding) for item in response.data]
