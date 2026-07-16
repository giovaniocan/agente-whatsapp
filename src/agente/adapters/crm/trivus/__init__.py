"""Adapter TrivusCRM — ver adapter.py. Vocabulário do Trivus vive SÓ aqui (RN-60)."""

from agente.adapters.crm.trivus.adapter import TrivusCRM
from agente.adapters.crm.trivus.errors import FeatureLockedError, TrivusError

__all__ = ["FeatureLockedError", "TrivusCRM", "TrivusError"]
