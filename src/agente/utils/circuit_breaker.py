"""
Circuit breaker simples (Plano 11.4).

Após N falhas seguidas, abre por T segundos: paramos de bater num serviço
caído (Z-API/CRM) em vez de empilhar timeouts. Passada a janela, meio-abre
(deixa UMA tentativa passar); sucesso fecha e zera.

Relógio injetável → testes determinísticos. A fiação nos adapters é feita
no bootstrap (quem decide o que fazer quando aberto é o chamador).
"""

import time
from collections.abc import Callable


class CircuitBreaker:
    def __init__(
        self,
        max_failures: int = 5,
        reset_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_failures = max_failures
        self._reset_seconds = reset_seconds
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None

    def allow(self) -> bool:
        if self._opened_at is None:
            return True
        if self._clock() - self._opened_at >= self._reset_seconds:
            # meio-aberto: libera uma tentativa; falhou de novo → reabre.
            self._opened_at = None
            self._failures = self._max_failures - 1
            return True
        return False

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._max_failures:
            self._opened_at = self._clock()
