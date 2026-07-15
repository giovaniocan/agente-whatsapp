"""
Smoke integrador (fecha M1 parcial): ficha → fábrica → CRM → agenda → agendamento.
Prova que as peças do Plano 02 e 03 se encaixam, ainda sem nada externo.
"""

from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from agente.adapters.crm.factory import build_crm
from agente.config.tenant_loader import load_tenant_file
from agente.domain.crm import AppointmentRequest
from agente.domain.scheduling import available_slots

TENANTS = Path(__file__).resolve().parents[2] / "src" / "agente" / "config" / "tenants"
SP = ZoneInfo("America/Sao_Paulo")
TUESDAY = date(2026, 7, 21)   # salão atende terça


async def test_full_scheduling_flow_in_memory() -> None:
    tenant = load_tenant_file(TENANTS / "salao_demo.json")
    crm = build_crm(tenant.crm)

    # 1. contato
    contact = await crm.create_contact("Maria Souza", "44999998888")

    # 2. disponibilidade do serviço "corte" na terça (Plano 02 + ficha)
    service = tenant.service_for("haircut")
    assert service is not None
    now = datetime(2026, 7, 21, 8, 0, tzinfo=SP)
    busy = await crm.get_scheduled_appointments(TUESDAY)
    slots = available_slots(tenant.scheduling, service, TUESDAY, busy, now=now)
    assert slots, "esperava horários livres na terça"

    # 3. agenda o primeiro slot livre
    chosen = slots[0]
    appt = await crm.create_appointment(
        AppointmentRequest(
            contact_id=contact.id,
            intent="haircut",
            start=chosen.start,
            end=chosen.end,
        )
    )

    # 4. aparece na agenda do dia
    agenda = await crm.get_scheduled_appointments(TUESDAY)
    assert appt.id in {a.id for a in agenda}
