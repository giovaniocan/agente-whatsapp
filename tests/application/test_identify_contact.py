"""Use case IdentifyOrCreateContact — nunca duplica (Plano 04.1)."""

from agente.adapters.crm.fake_crm import FakeCRM
from agente.application.identify_contact import IdentifyOrCreateContact


async def test_creates_contact_when_phone_is_new() -> None:
    crm = FakeCRM()
    use_case = IdentifyOrCreateContact(crm)

    contact = await use_case.execute(full_name="João Silva", phone="44999998888")

    assert contact.id
    assert contact.full_name == "João Silva"


async def test_returns_existing_contact_without_duplicating() -> None:
    crm = FakeCRM()
    first = await crm.create_contact("João Silva", "44999998888")
    use_case = IdentifyOrCreateContact(crm)

    # mesma pessoa, telefone na variante sem o 9º dígito (RN-22)
    again = await use_case.execute(full_name="João", phone="4499998888")

    assert again.id == first.id
