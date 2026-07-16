"""Bootstrap de produção (Plano 11) — monta tudo a partir das fichas reais."""

from pathlib import Path

from agente.bootstrap import build_runtime
from agente.config.settings import Settings

TENANTS = Path(__file__).resolve().parents[2] / "src" / "agente" / "config" / "tenants"


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://agente:agente@localhost:5439/agente",
        tenants_dir=str(TENANTS),
    )


def test_runtime_loads_ready_tenants_and_skips_pending_adapters() -> None:
    runtime = build_runtime(_settings())

    # salão (crm fake) entra; revenda (crm trivus, plano 08 pendente) é pulada
    assert "salao_demo" in runtime.registry_by_id
    assert "revenda_veiculos" not in runtime.registry_by_id
    assert "salao_demo" in runtime.pipelines


def test_runtime_app_exposes_health_and_webhook() -> None:
    runtime = build_runtime(_settings())
    paths = {route.path for route in runtime.app.routes}  # type: ignore[attr-defined]
    assert "/health" in paths
    assert "/webhook/whatsapp/{token}" in paths


def test_runtime_builds_worker_with_handlers() -> None:
    worker = build_runtime(_settings()).build_worker()
    assert worker is not None
