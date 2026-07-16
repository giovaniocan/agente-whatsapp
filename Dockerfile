# Agente WhatsApp — imagem única p/ api e worker (Plano 11)
# api    (default): migrations + uvicorn
# worker (Coolify: sobrescrever o CMD): python -m agente.worker

FROM python:3.12-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# deps primeiro (camada cacheável)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# código + migrations
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# migrations no boot (guia do trivus-api); worker sobrescreve o CMD
CMD ["sh", "-c", "alembic upgrade head && uvicorn agente.api.main:app --host 0.0.0.0 --port 8000"]
