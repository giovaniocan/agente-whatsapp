"""Circuit breaker (Plano 11.4) — abre após N falhas, meio-abre após T."""

from agente.utils.circuit_breaker import CircuitBreaker


def test_opens_after_max_failures() -> None:
    clock = [100.0]
    cb = CircuitBreaker(max_failures=3, reset_seconds=30, clock=lambda: clock[0])

    assert cb.allow()
    for _ in range(3):
        cb.record_failure()

    assert not cb.allow()                      # aberto: para de bater no serviço


def test_half_opens_after_reset_window() -> None:
    clock = [100.0]
    cb = CircuitBreaker(max_failures=1, reset_seconds=30, clock=lambda: clock[0])
    cb.record_failure()
    assert not cb.allow()

    clock[0] += 31                             # janela passou → tenta de novo
    assert cb.allow()


def test_success_closes_and_resets() -> None:
    clock = [100.0]
    cb = CircuitBreaker(max_failures=2, reset_seconds=30, clock=lambda: clock[0])
    cb.record_failure()
    cb.record_success()                        # sucesso zera o contador
    cb.record_failure()
    assert cb.allow()                          # 1 falha < 2 → segue fechado
