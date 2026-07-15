"""
Erros da camada de aplicação.

São erros de REGRA de negócio (não de infraestrutura). O cérebro (LLM) os usa
para conversar: "faltou o nome", "esse horário lotou, tente outro".
"""


class InvalidIntentError(Exception):
    """Intent fora do vocabulário declarado do tenant (RN-02)."""

    def __init__(self, intent: str, allowed: list[str]) -> None:
        self.intent = intent
        self.allowed = allowed
        super().__init__(
            f"intent {intent!r} não é válida; permitidas: {sorted(allowed)}"
        )


class MissingLeadDataError(Exception):
    """Faltam dados obrigatórios para agendar (RN-20). Lista o que falta."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(f"dados obrigatórios ausentes: {missing}")


class SlotTakenError(Exception):
    """O horário pedido não está mais disponível (RN-13). Traz alternativas."""

    def __init__(self, alternatives: list[str]) -> None:
        self.alternatives = alternatives
        super().__init__("horário indisponível; ofereça alternativas")
