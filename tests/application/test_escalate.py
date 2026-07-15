"""EscalateToHuman — ordem do RN-31 e fallback de falha (Plano 04.5)."""

from collections.abc import Callable
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from agente.adapters.crm.fake_crm import FakeCRM
from agente.adapters.scheduler.fake_scheduler import FakeScheduler
from agente.adapters.whatsapp.fake_whatsapp import FakeWhatsApp
from agente.application.escalate import EscalateToHuman
from agente.domain.conversation import Conversation
from agente.domain.enums import EscalationTrigger, HandoffStatus
from agente.domain.tenant import HandoffConfig, Tenant

SP = ZoneInfo("America/Sao_Paulo")
NOW = datetime(2026, 7, 20, 10, 0, tzinfo=SP)


def _tenant(make_tenant: Callable[..., Tenant]) -> Tenant:
    return make_tenant(
        handoff=HandoffConfig(team_phone="5511999990000", auto_resume_hours=4)
    )


def _conv() -> Conversation:
    return Conversation(tenant_id="salao", phone="44999998888", summary="cliente irritado")


async def test_escalation_follows_rn31(make_tenant: Callable[..., Tenant]) -> None:
    crm, wpp, sched = FakeCRM(), FakeWhatsApp(), FakeScheduler()
    conv = _conv()
    uc = EscalateToHuman(_tenant(make_tenant), crm, wpp, sched)

    await uc.execute(
        conversation=conv,
        contact_id="c1",
        reason=EscalationTrigger.EXPLICIT_REQUEST,
        now=NOW,
    )

    assert conv.handoff_status is HandoffStatus.PENDING     # (1) IA calada
    assert len(crm.handoff_tasks) == 1                      # (3) tarefa no CRM
    assert crm.handoff_tasks[0].reason is EscalationTrigger.EXPLICIT_REQUEST
    recipients = [phone for phone, _ in wpp.sent]
    assert "5511999990000" in recipients                   # (4) time avisado
    assert "44999998888" in recipients                     # (5) cliente avisado
    resume_jobs = [j for j in sched.jobs.values() if j.kind == "auto_resume"]  # (6)
    assert resume_jobs and resume_jobs[0].run_at == NOW + timedelta(hours=4)


async def test_status_is_pending_before_any_io(
    make_tenant: Callable[..., Tenant],
) -> None:
    # RN-31.1: a IA para ANTES de qualquer I/O — quando o CRM é chamado, já é PENDING.
    seen: dict[str, HandoffStatus] = {}
    conv = _conv()

    class SpyCRM(FakeCRM):
        async def create_handoff_task(self, task):  # type: ignore[no-untyped-def]
            seen["status"] = conv.handoff_status
            await super().create_handoff_task(task)

    uc = EscalateToHuman(_tenant(make_tenant), SpyCRM(), FakeWhatsApp(), FakeScheduler())
    await uc.execute(
        conversation=conv, contact_id="c1", reason=EscalationTrigger.DISSATISFACTION, now=NOW
    )
    assert seen["status"] is HandoffStatus.PENDING


async def test_team_notified_even_if_crm_fails(
    make_tenant: Callable[..., Tenant],
) -> None:
    # RN-31: se a tarefa no CRM falhar, o time é avisado mesmo assim e a IA NÃO volta.
    wpp, sched = FakeWhatsApp(), FakeScheduler()
    conv = _conv()

    class BrokenCRM(FakeCRM):
        async def create_handoff_task(self, task):  # type: ignore[no-untyped-def]
            raise RuntimeError("CRM fora do ar")

    uc = EscalateToHuman(_tenant(make_tenant), BrokenCRM(), wpp, sched)
    await uc.execute(
        conversation=conv, contact_id="c1", reason=EscalationTrigger.OUT_OF_RULES, now=NOW
    )

    assert "5511999990000" in [phone for phone, _ in wpp.sent]   # time avisado
    assert conv.handoff_status is HandoffStatus.PENDING          # IA continua calada
