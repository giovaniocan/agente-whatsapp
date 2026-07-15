"""Embedders (Plano 10.2) — fake determinístico e OpenAI (SDK mockada)."""

from types import SimpleNamespace

from agente.adapters.vectorstore.embedder import FakeEmbedder, OpenAIEmbedder


async def test_fake_embedder_is_deterministic_and_normalized() -> None:
    emb = FakeEmbedder(dim=32)
    [a1], [a2] = await emb.embed(["unha em gel"]), await emb.embed(["unha em gel"])
    assert a1 == a2                                   # determinístico
    assert abs(sum(x * x for x in a1) - 1.0) < 1e-6   # normalizado


async def test_fake_embedder_similar_texts_are_closer() -> None:
    emb = FakeEmbedder(dim=32)
    [gel], [promo], [carro] = (
        await emb.embed(["unha em gel"]),
        await emb.embed(["promoção de unha em gel"]),
        await emb.embed(["financiamento de carro usado"]),
    )
    def cos(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b, strict=True))
    assert cos(gel, promo) > cos(gel, carro)          # sobreposição de palavras conta


async def test_openai_embedder_translates_response() -> None:
    class _Embeddings:
        async def create(self, **kwargs: object) -> object:
            self.last = kwargs
            return SimpleNamespace(
                data=[SimpleNamespace(embedding=[0.1, 0.2]), SimpleNamespace(embedding=[0.3, 0.4])]
            )

    client = SimpleNamespace(embeddings=_Embeddings())
    emb = OpenAIEmbedder(model="text-embedding-3-small", client=client)

    vectors = await emb.embed(["a", "b"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert client.embeddings.last["model"] == "text-embedding-3-small"
