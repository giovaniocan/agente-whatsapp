"""
Raiz de composição dos handlers de ferramenta.

Traduz cada `ToolCall` (nome + args do LLM) para o use case correspondente,
devolvendo um texto de resultado que o LLM usa para redigir a resposta final.
Erros de negócio (RN-13/RN-20) viram texto para o LLM conversar, não exceção.
"""

from collections.abc import Awaitable, Callable, Mapping
from datetime import date, datetime

from agente.application.cancel_appointment import CancelAppointment
from agente.application.errors import MissingLeadDataError, SlotTakenError
from agente.application.escalate import EscalateToHuman
from agente.application.get_availability import GetAvailability
from agente.application.identify_contact import IdentifyOrCreateContact
from agente.application.qualify_lead import QualifyLead
from agente.application.reschedule_appointment import RescheduleAppointment
from agente.application.schedule_appointment import ScheduleAppointment
from agente.domain.conversation import Conversation
from agente.domain.enums import EscalationTrigger, LeadPriority
from agente.domain.lead import LeadInfo
from agente.domain.ports import CRMPort, KnowledgePort, SchedulerPort, WhatsAppPort
from agente.domain.tenant import Tenant

ToolHandler = Callable[[dict[str, object]], Awaitable[str]]


def build_handlers(
    tenant: Tenant,
    crm: CRMPort,
    scheduler: SchedulerPort,
    whatsapp: WhatsAppPort,
    conversation: Conversation,
    now: datetime,
    knowledge: KnowledgePort | None = None,
) -> Mapping[str, ToolHandler]:
    phone = conversation.phone

    async def _contact_id(full_name: str) -> str:
        contact = await IdentifyOrCreateContact(crm).execute(full_name, phone)
        return contact.id

    async def get_availability(args: dict[str, object]) -> str:
        slots = await GetAvailability(tenant, crm).execute(
            intent=str(args["intent"]), day=date.fromisoformat(str(args["day"])), now=now
        )
        if not slots:
            return "nenhum horário livre nesse dia"
        return "; ".join(s.start.strftime("%d/%m %H:%M") for s in slots[:5])

    async def schedule_appointment(args: dict[str, object]) -> str:
        full_name = str(args["full_name"])
        draft = LeadInfo(
            full_name=full_name,
            phone=phone,
            intent=str(args["intent"]),
            notes=str(args["notes"]) if args.get("notes") else None,
        )
        conversation.lead_draft = draft
        contact_id = await _contact_id(full_name)
        try:
            appt = await ScheduleAppointment(tenant, crm, scheduler).execute(
                draft=draft,
                contact_id=contact_id,
                start=datetime.fromisoformat(str(args["start"])),
                now=now,
            )
        except SlotTakenError as exc:
            return f"horário indisponível; ofereça: {exc.alternatives}"
        except MissingLeadDataError as exc:
            return f"faltam dados: {exc.missing}"
        return f"agendado para {appt.start.isoformat()}"

    async def reschedule_appointment(args: dict[str, object]) -> str:
        try:
            appt = await RescheduleAppointment(tenant, crm, scheduler).execute(
                appointment_id=str(args["appointment_id"]),
                new_start=datetime.fromisoformat(str(args["new_start"])),
                phone=phone,
                now=now,
            )
        except SlotTakenError as exc:
            return f"horário indisponível; ofereça: {exc.alternatives}"
        return f"reagendado para {appt.start.isoformat()}"

    async def cancel_appointment(args: dict[str, object]) -> str:
        await CancelAppointment(crm, scheduler).execute(str(args["appointment_id"]))
        return "cancelado"

    async def qualify_lead(args: dict[str, object]) -> str:
        name = conversation.lead_draft.full_name if conversation.lead_draft else "cliente"
        contact_id = await _contact_id(name)
        await QualifyLead(tenant, crm).execute(
            contact_id,
            intent=str(args["intent"]),
            priority=LeadPriority(str(args["priority"])),
            notes=str(args["notes"]) if args.get("notes") else None,
        )
        return "qualificado"

    async def escalate_to_human(args: dict[str, object]) -> str:
        name = conversation.lead_draft.full_name if conversation.lead_draft else "cliente"
        contact_id = await _contact_id(name)
        await EscalateToHuman(tenant, crm, whatsapp, scheduler).execute(
            conversation=conversation,
            contact_id=contact_id,
            reason=EscalationTrigger(str(args["reason"])),
            now=now,
            routing_hint=str(args["routing_hint"]) if args.get("routing_hint") else None,
        )
        return "escalado"

    async def search_knowledge(args: dict[str, object]) -> str:
        if knowledge is None:
            return "base de conhecimento indisponível — diga que vai confirmar com o time"
        chunks = await knowledge.search(tenant.id, str(args["query"]), k=3)
        if not chunks:
            # reforço da RN-30: sem fonte, o LLM não inventa preço/condição.
            return "nada encontrado — diga que vai confirmar com o time; não invente"
        return "\n---\n".join(chunks)

    return {
        "get_availability": get_availability,
        "schedule_appointment": schedule_appointment,
        "reschedule_appointment": reschedule_appointment,
        "cancel_appointment": cancel_appointment,
        "qualify_lead": qualify_lead,
        "escalate_to_human": escalate_to_human,
        "search_knowledge": search_knowledge,
    }
