"""Chunking de texto para o RAG (Plano 10.2)."""

from agente.utils.chunking import chunk_text


def test_short_text_is_one_chunk() -> None:
    assert chunk_text("FAQ curta.", max_chars=500) == ["FAQ curta."]


def test_long_text_splits_with_overlap() -> None:
    text = " ".join(f"palavra{i}" for i in range(400))   # bem maior que 500 chars

    chunks = chunk_text(text, max_chars=500, overlap=100)

    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks)
    # overlap: o começo de cada chunk repete o fim do anterior (contexto contínuo)
    assert chunks[1][:50] in chunks[0]


def test_paragraphs_are_respected_when_possible() -> None:
    text = "Parágrafo A.\n\nParágrafo B.\n\nParágrafo C."
    chunks = chunk_text(text, max_chars=500)
    assert chunks == [text]                                # cabe inteiro → 1 chunk


def test_empty_text_yields_nothing() -> None:
    assert chunk_text("   \n  ", max_chars=500) == []
