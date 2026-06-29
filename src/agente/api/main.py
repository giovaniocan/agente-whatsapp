from fastapi import FastAPI

from agente.config.settings import settings

app = FastAPI(title="Agente WhatsApp")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "evolution_url": settings.evolution_api_url,
    }
