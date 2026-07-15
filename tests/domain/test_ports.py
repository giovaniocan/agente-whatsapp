"""A CRMPort é um contrato estrutural (Protocol) — qualquer classe com os
métodos certos serve, sem herança."""

from agente.domain.ports import CRMPort


class _FullCrm:
    async def find_contact_by_phone(self, phone: str):  # type: ignore[no-untyped-def]
        ...

    async def create_contact(self, full_name, phone, email=None):  # type: ignore[no-untyped-def]
        ...

    async def update_lead_qualification(self, contact_id, intent, priority, notes=None):  # type: ignore[no-untyped-def]  # noqa: E501
        ...

    async def get_scheduled_appointments(self, day):  # type: ignore[no-untyped-def]
        ...

    async def create_appointment(self, request):  # type: ignore[no-untyped-def]
        ...

    async def cancel_appointment(self, appointment_id):  # type: ignore[no-untyped-def]
        ...

    async def reschedule_appointment(self, appointment_id, new_start):  # type: ignore[no-untyped-def]  # noqa: E501
        ...

    async def create_handoff_task(self, task):  # type: ignore[no-untyped-def]
        ...


class _PartialCrm:
    async def find_contact_by_phone(self, phone: str):  # type: ignore[no-untyped-def]
        ...


def test_full_impl_satisfies_crmport() -> None:
    assert isinstance(_FullCrm(), CRMPort)


def test_incomplete_impl_does_not_satisfy_crmport() -> None:
    assert not isinstance(_PartialCrm(), CRMPort)
