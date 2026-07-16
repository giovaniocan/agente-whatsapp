"""Erros do adapter Trivus."""


class TrivusError(Exception):
    """Resposta inesperada/erro do trivus-api (RN-61: falhar cedo e claro)."""


class FeatureLockedError(TrivusError):
    """403 feature_locked — plano da loja não inclui o recurso (RN-64, sem retry)."""

    def __init__(self, feature_key: str) -> None:
        self.feature_key = feature_key
        super().__init__(f"recurso bloqueado pelo plano da loja: {feature_key!r}")
