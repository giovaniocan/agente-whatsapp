"""
Observabilidade (Plano 11.3) — logs estruturados SEM PII.

Regra: telefone jamais aparece em claro num log. `log_event` hasheia
automaticamente qualquer campo cujo nome contenha "phone". O hash é estável,
então dá para seguir uma conversa nos logs sem expor o número (LGPD).
"""

import hashlib
import logging
from typing import Any


def hash_phone(phone: str) -> str:
    return hashlib.sha256(phone.encode()).hexdigest()[:10]


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    safe: dict[str, Any] = {}
    for key, value in fields.items():
        if "phone" in key.lower() and value:
            safe[key] = hash_phone(str(value))
        else:
            safe[key] = value
    parts = " ".join(f"{k}={v}" for k, v in safe.items())
    logger.info("%s %s", event, parts)
