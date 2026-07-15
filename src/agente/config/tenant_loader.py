"""
Loader de fichas de tenant.

Carrega o JSON, resolve referências de segredo (`env:NOME` → variável de
ambiente, RN-63), rejeita segredo literal, e valida com Pydantic (RN-61). Um
erro aqui é um erro de BOOT — melhor falhar cedo e claro do que rodar torto.
"""

import json
import os
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from agente.domain.tenant import Tenant

_ENV_PREFIX = "env:"


class TenantConfigError(Exception):
    """Ficha de tenant inválida (segredo literal, intent órfã, JSON torto…)."""


def _resolve_secret(value: str, field: str) -> str:
    if not value:
        return value
    if value.startswith(_ENV_PREFIX):
        return os.environ.get(value[len(_ENV_PREFIX) :], "")
    raise TenantConfigError(
        f"{field}: segredo literal proibido (RN-63); use 'env:NOME_DA_VARIAVEL'"
    )


def load_tenant_from_dict(data: dict[str, Any]) -> Tenant:
    crm = data.get("crm")
    if isinstance(crm, dict) and "api_key" in crm:
        crm["api_key"] = _resolve_secret(str(crm["api_key"]), "crm.api_key")
    try:
        return Tenant.model_validate(data)
    except ValidationError as exc:
        raise TenantConfigError(f"ficha inválida: {exc}") from exc


def load_tenant_file(path: Path) -> Tenant:
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise TenantConfigError(f"não consegui ler a ficha {path}: {exc}") from exc
    return load_tenant_from_dict(data)
