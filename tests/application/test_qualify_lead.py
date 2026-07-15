"""Use case QualifyLead — grava qualificação, valida intent (Plano 04.2)."""

from collections.abc import Callable

import pytest

from agente.adapters.crm.fake_crm import FakeCRM
from agente.application.errors import InvalidIntentError
from agente.application.qualify_lead import QualifyLead
from agente.domain.enums import LeadPriority
from agente.domain.tenant import Tenant


async def test_qualification_is_written_to_crm(make_tenant: Callable[..., Tenant]) -> None:
    crm = FakeCRM()
    contact = await crm.create_contact("Maria", "44999998888")
    use_case = QualifyLead(make_tenant(), crm)

    await use_case.execute(
        contact.id, intent="haircut", priority=LeadPriority.HIGH, notes="urgente"
    )

    updated = await crm.find_contact_by_phone("44999998888")
    assert updated is not None
    assert updated.intent == "haircut"
    assert updated.priority is LeadPriority.HIGH


async def test_intent_outside_tenant_is_rejected(
    make_tenant: Callable[..., Tenant],
) -> None:
    # RN-02: "buy_vehicle" não existe no salão.
    crm = FakeCRM()
    contact = await crm.create_contact("Maria", "44999998888")
    use_case = QualifyLead(make_tenant(), crm)

    with pytest.raises(InvalidIntentError):
        await use_case.execute(
            contact.id, intent="buy_vehicle", priority=LeadPriority.MEDIUM
        )
