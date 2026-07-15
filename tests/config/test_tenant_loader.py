"""Loader de fichas de tenant — valida no boot (RN-61) e resolve segredos (RN-63)."""

import json
from pathlib import Path

import pytest

from agente.config.tenant_loader import (
    TenantConfigError,
    load_tenant_file,
    load_tenant_from_dict,
)

TENANTS_DIR = Path(__file__).resolve().parents[2] / "src" / "agente" / "config" / "tenants"


def _valid_dict() -> dict:
    return json.loads((TENANTS_DIR / "salao_demo.json").read_text())


def test_real_fichas_load() -> None:
    revenda = load_tenant_file(TENANTS_DIR / "revenda_veiculos.json")
    salao = load_tenant_file(TENANTS_DIR / "salao_demo.json")
    assert revenda.id == "revenda_veiculos"
    assert salao.service_for("nails").capacity == 1   # RN-11 preservado


def test_env_reference_is_resolved(monkeypatch: pytest.MonkeyPatch) -> None:
    # RN-63: api_key "env:NOME" vira o valor real da variável de ambiente.
    monkeypatch.setenv("TRIVUS_TOKEN_REVENDA_VEICULOS", "segredo-123")
    revenda = load_tenant_file(TENANTS_DIR / "revenda_veiculos.json")
    assert revenda.crm.api_key == "segredo-123"


def test_literal_api_key_is_rejected() -> None:
    # RN-63: ficha commitada não pode ter segredo literal.
    data = _valid_dict()
    data["crm"] = {"type": "trivus", "api_key": "sk-live-hardcoded"}
    with pytest.raises(TenantConfigError):
        load_tenant_from_dict(data)


def test_orphan_intent_fails_at_load() -> None:
    # RN-02/RN-61: serviço apontando para intent não declarada → erro claro.
    data = _valid_dict()
    data["intents"] = ["haircut"]
    data["services"] = [
        {"name": "Unha", "intent": "nails", "duration_minutes": 60, "capacity": 1}
    ]
    with pytest.raises(TenantConfigError):
        load_tenant_from_dict(data)
