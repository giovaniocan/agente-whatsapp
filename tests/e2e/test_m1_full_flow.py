"""
E2E do Marco M1: o fluxo de atendimento inteiro, só com fakes.
contato → qualifica → disponibilidade → agenda (+lembretes) → handoff → IA cala.
"""

from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from agente.adapters.crm.fake_crm import FakeCRM
from agente.adapters.scheduler.fake_scheduler import FakeScheduler
from agente.adapters.whatsapp.fake_whatsapp import FakeWhatsApp
from agente.application.escalate import EscalateToHuman
from agente.application.get_availability import GetAvailability
from agente.application.identify_contact import IdentifyOrCreateContact
from agente.application.qualify_lead import QualifyLead
from agente.application.schedule_appointment import ScheduleAppointment
from agente.config.tenant_loader import load_tenant_file
from agente.domain.conversation import Conversation
from agente.domain.enums import EscalationTrigger, HandoffStatus, LeadPriority
from agente.domain.lead import LeadInfo
from agente.domain.tenant import HandoffConfig

TENANTS = Path(__file__).resolve().parents[2] / "src" / "agente" / "config" / "tenants"
SP = ZoneInfo("America/Sao_Paulo")
TUESDAY = date(2026, 7, 21)
NOW = datetime(2026, 7, 21, 8, 0, tzinfo=SP)


async def test_full_attendance_flow_with_fakes() -> None:
    tenant = load_tenant_file(TENANTS / "salao_demo.json").model_copy(
        update={"handoff": HandoffConfig(team_phone="5511999990000", auto_resume_hours=4)}
    )
    crm, sched, wpp = FakeCRM(), FakeScheduler(), FakeWhatsApp()
    phone = "44999998888"

    # 1. contato
    contact = await IdentifyOrCreateContact(crm).execute("Maria Souza", phone)

    # 2. qualificação
    await QualifyLead(tenant, crm).execute(
        contact.id, intent="nails", priority=LeadPriority.HIGH, notes="quer unha em gel"
    )

    # 3. disponibilidade + 4. agendamento
    slots = await GetAvailability(tenant, crm).execute("nails", TUESDAY, now=NOW)
    assert slots
    draft = LeadInfo(full_name="Maria Souza", phone=phone, intent="nails")
    appt = await ScheduleAppointment(tenant, crm, sched).execute(
        draft=draft, contact_id=contact.id, start=slots[0].start, now=NOW
    )
    assert appt.id in {a.id for a in await crm.get_scheduled_appointments(TUESDAY)}
    assert len([j for j in sched.jobs.values() if j.kind == "reminder"]) == 3

    # 5. handoff → IA cala
    conv = Conversation(tenant_id=tenant.id, phone=phone, lead_draft=draft)
    await EscalateToHuman(tenant, crm, wpp, sched).execute(
        conversation=conv,
        contact_id=contact.id,
        reason=EscalationTrigger.EXPLICIT_REQUEST,
        now=NOW,
    )

    assert conv.handoff_status is HandoffStatus.PENDING
    assert conv.can_ai_reply is False
    assert len(crm.handoff_tasks) == 1
    assert phone in [p for p, _ in wpp.sent]                       # cliente avisado
    assert any(j.kind == "auto_resume" for j in sched.jobs.values())
