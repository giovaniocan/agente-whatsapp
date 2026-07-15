"""Testes da entidade Conversation e sua máquina de handoff (RN-31)."""

from agente.domain.conversation import Conversation
from agente.domain.enums import HandoffStatus


def _conv() -> Conversation:
    return Conversation(tenant_id="t1", phone="44999998888")


def test_new_conversation_is_active_and_ai_can_reply() -> None:
    conv = _conv()
    assert conv.handoff_status is HandoffStatus.ACTIVE
    assert conv.can_ai_reply is True


def test_request_handoff_sets_pending_and_blocks_ai() -> None:
    # RN-31.1: ao escalar, a IA para de responder imediatamente.
    conv = _conv()
    conv.request_handoff()
    assert conv.handoff_status is HandoffStatus.PENDING
    assert conv.can_ai_reply is False


def test_human_took_over_moves_to_human_and_blocks_ai() -> None:
    conv = _conv()
    conv.request_handoff()
    conv.human_took_over()
    assert conv.handoff_status is HandoffStatus.HUMAN
    assert conv.can_ai_reply is False


def test_resume_returns_control_to_ai() -> None:
    # RN-31.6: auto-resume devolve o comando à IA.
    conv = _conv()
    conv.request_handoff()
    conv.resume()
    assert conv.handoff_status is HandoffStatus.ACTIVE
    assert conv.can_ai_reply is True


def test_updated_at_is_timezone_aware() -> None:
    # RN-14: nada de datetime naïve no domínio.
    assert _conv().updated_at.tzinfo is not None


def test_transition_bumps_updated_at() -> None:
    conv = _conv()
    before = conv.updated_at
    conv.request_handoff()
    assert conv.updated_at >= before
