"""
FakeCRM — implementação em memória da CRMPort.

Serve para testes e para o agente rodar ponta a ponta sem CRM externo. Cada
instância é isolada (RN-03): tem seus próprios dicionários. Busca por telefone
usa as variantes do 9º dígito (RN-22).
"""

from datetime import date, datetime
from uuid import uuid4

from agente.domain.crm import Appointment, AppointmentRequest, Contact, HandoffTask
from agente.domain.enums import AppointmentStatus, LeadPriority
from agente.utils.phone import only_digits, phone_variants


class FakeCRM:
    def __init__(self) -> None:
        self._contacts: dict[str, Contact] = {}
        self._appointments: dict[str, Appointment] = {}
        self.handoff_tasks: list[HandoffTask] = []

    async def find_contact_by_phone(self, phone: str) -> Contact | None:
        wanted = set(phone_variants(phone))
        for contact in self._contacts.values():
            if only_digits(contact.phone) in wanted:
                return contact
        return None

    async def create_contact(
        self, full_name: str, phone: str, email: str | None = None
    ) -> Contact:
        contact = Contact(id=uuid4().hex, full_name=full_name, phone=phone, email=email)
        self._contacts[contact.id] = contact
        return contact

    async def update_lead_qualification(
        self,
        contact_id: str,
        intent: str,
        priority: LeadPriority,
        notes: str | None = None,
    ) -> None:
        contact = self._contacts[contact_id]
        self._contacts[contact_id] = contact.model_copy(
            update={"intent": intent, "priority": priority, "notes": notes}
        )

    async def get_scheduled_appointments(self, day: date) -> list[Appointment]:
        return [
            a
            for a in self._appointments.values()
            if a.status is AppointmentStatus.SCHEDULED and a.start.date() == day
        ]

    async def create_appointment(self, request: AppointmentRequest) -> Appointment:
        appt = Appointment(
            id=uuid4().hex,
            contact_id=request.contact_id,
            intent=request.intent,
            start=request.start,
            end=request.end,
        )
        self._appointments[appt.id] = appt
        return appt

    async def cancel_appointment(self, appointment_id: str) -> None:
        self._appointments.pop(appointment_id)   # KeyError se não existir (falha cedo)

    async def reschedule_appointment(
        self, appointment_id: str, new_start: datetime
    ) -> Appointment:
        current = self._appointments[appointment_id]
        duration = current.end - current.start
        moved = current.model_copy(update={"start": new_start, "end": new_start + duration})
        self._appointments[appointment_id] = moved
        return moved

    async def create_handoff_task(self, task: HandoffTask) -> None:
        self.handoff_tasks.append(task)
