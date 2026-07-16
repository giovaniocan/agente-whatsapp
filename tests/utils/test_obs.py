"""Observabilidade (Plano 11.3): telefone NUNCA em claro nos logs (LGPD)."""

import logging

from agente.utils.obs import hash_phone, log_event


def test_hash_phone_is_stable_and_short() -> None:
    a, b = hash_phone("44999998888"), hash_phone("44999998888")
    assert a == b and len(a) == 10
    assert "4499999" not in a                       # não é o número


def test_log_event_hashes_any_phone_field(caplog) -> None:  # type: ignore[no-untyped-def]
    logger = logging.getLogger("test.obs")
    with caplog.at_level(logging.INFO):
        log_event(
            logger,
            "message_processed",
            tenant_id="salao",
            phone="44999998888",
            team_phone="5511999990000",
            tokens_out=42,
        )

    output = caplog.text
    assert "44999998888" not in output              # RN do plano 11: sem PII
    assert "5511999990000" not in output
    assert hash_phone("44999998888") in output      # rastreável via hash
    assert "message_processed" in output and "tokens_out=42" in output
