"""Chunking simples com overlap para o RAG (RN — plano 10.2).

Janela deslizante por caracteres com sobreposição: simples, determinístico e
suficiente para FAQ/políticas. Refinamentos (sentença/token) só se a busca
real mostrar necessidade (YAGNI).
"""


def chunk_text(text: str, max_chars: int = 500, overlap: int = 100) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    step = max(max_chars - overlap, 1)
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        chunks.append(cleaned[start : start + max_chars])
        start += step
    return chunks
