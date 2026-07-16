"""
TrivusCRM — o adapter real (CRMPort ↔ REST do trivus-api). Fecha o M3.

Comportamento confirmado com payloads reais (docs/trivus/INTEGRACAO_AGENTE.md):
- sem busca por telefone → lista completa + filtro local (variantes 9º dígito);
- stage_id obrigatório no POST → resolve e CACHEIA a 1ª etapa do funil;
- a API duplica → dedupe é do chamador (find-then-create + lock por conversa);
- observacoes SOBRESCREVE e não há GET por id → append manual via lista;
- agendamento não registra o serviço → Appointment sai com intent="" e a ficha
  da revenda usa scheduling.shared_capacity=true (capacidade da LOJA).
"""

from datetime import date, datetime, timedelta

import httpx

from agente.adapters.crm.trivus.auth import TrivusAuth
from agente.adapters.crm.trivus.dtos import TrivusAgendaPage, TrivusFunnel, TrivusLead
from agente.adapters.crm.trivus.errors import FeatureLockedError, TrivusError
from agente.adapters.crm.trivus.trivus_time import from_trivus, to_trivus
from agente.domain.crm import Appointment, AppointmentRequest, Contact, HandoffTask
from agente.domain.enums import LeadPriority
from agente.domain.tenant import CRMConfig
from agente.utils.phone import only_digits, phone_variants

_PRIORITY_TO_URGENCIA = {
    LeadPriority.HIGH: "alta",
    LeadPriority.MEDIUM: "media",
    LeadPriority.LOW: "baixa",
}
_URGENCIA_TO_PRIORITY = {v: k for k, v in _PRIORITY_TO_URGENCIA.items()}
_PAGE_SIZE = 100


class TrivusCRM:
    def __init__(self, config: CRMConfig, client: httpx.AsyncClient | None = None) -> None:
        self._store_id = config.settings.get("store_id", "")
        self._handoff_user_id = config.settings.get("handoff_user_id") or None
        self._minutes = int(config.settings.get("appointment_minutes", "60"))
        self._client = client or httpx.AsyncClient(base_url=config.base_url, timeout=15.0)
        self._auth = TrivusAuth(
            self._client, email=config.settings.get("email", ""), password=config.api_key
        )
        self._stage_id: str | None = None   # cache da 1ª etapa (por instância=loja)

    # ---------- HTTP com re-login e tradução de erros ----------

    async def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        resp: httpx.Response | None = None
        for attempt in (1, 2):
            token = await self._auth.token()
            resp = await self._client.request(
                method, path, headers={"Authorization": f"Bearer {token}"}, **kwargs  # type: ignore[arg-type]
            )
            if resp.status_code == 401 and attempt == 1:
                self._auth.invalidate()          # RN-64: re-login UMA vez
                continue
            break
        assert resp is not None
        self._raise_for_error(resp)
        return resp

    @staticmethod
    def _raise_for_error(resp: httpx.Response) -> None:
        if resp.status_code < 400:
            return
        try:
            body = resp.json()
        except ValueError:
            body = {}
        if resp.status_code == 403 and body.get("error") == "feature_locked":
            raise FeatureLockedError(str(body.get("feature_key", "")))
        # 400/401/403/404 = {"error": ...}; 422 = {"detail": [...]} (FastAPI)
        detail = body.get("error") or body.get("detail") or resp.text
        raise TrivusError(f"trivus-api {resp.status_code}: {detail}")

    # ---------- leituras internas ----------

    async def _list_leads(self) -> list[TrivusLead]:
        resp = await self._request("GET", "/crm/leads", params={"store_id": self._store_id})
        return [TrivusLead.model_validate(item) for item in resp.json()]

    async def _get_lead(self, lead_id: str) -> TrivusLead:
        # não existe GET /crm/leads/{id} — lista completa + filtro local.
        for lead in await self._list_leads():
            if lead.id == lead_id:
                return lead
        raise TrivusError(f"lead {lead_id} não encontrado na loja")

    async def _initial_stage_id(self) -> str:
        if self._stage_id is None:
            resp = await self._request(
                "GET", "/crm/funnels", params={"store_id": self._store_id}
            )
            funnels = [TrivusFunnel.model_validate(f) for f in resp.json()]
            if not funnels or not funnels[0].stages:
                raise TrivusError("loja sem funil/etapas — configure o funil no Trivus")
            self._stage_id = min(funnels[0].stages, key=lambda s: s.sort_order).id
        return self._stage_id

    async def _appended_observacoes(self, lead_id: str, text: str) -> str:
        # o PATCH SOBRESCREVE observacoes → append manual (corrida aceita na v1).
        current = (await self._get_lead(lead_id)).observacoes or ""
        return f"{current}\n{text}".strip()

    # ---------- CRMPort ----------

    async def find_contact_by_phone(self, phone: str) -> Contact | None:
        wanted = set(phone_variants(phone))
        digits = only_digits(phone)
        if digits:
            wanted.add(digits)
        matches = [
            lead
            for lead in await self._list_leads()
            if (lead.telefone and only_digits(lead.telefone) in wanted)
            or (lead.lid and lead.lid in wanted)
        ]
        if not matches:
            return None
        matches.sort(key=lambda lead: lead.created_at or "")   # o mais antigo vence
        return self._to_contact(matches[0])

    async def create_contact(
        self, full_name: str, phone: str, email: str | None = None
    ) -> Contact:
        # o lead do Trivus não tem e-mail — o campo é descartado aqui.
        stage_id = await self._initial_stage_id()
        resp = await self._request(
            "POST",
            "/crm/leads",
            json={
                "store_id": self._store_id,
                "stage_id": stage_id,
                "funil": "receptivo",
                "nome": full_name,
                "telefone": phone,
            },
        )
        return self._to_contact(TrivusLead.model_validate(resp.json()))

    async def update_lead_qualification(
        self,
        contact_id: str,
        intent: str,
        priority: LeadPriority,
        notes: str | None = None,
    ) -> None:
        note = f"[IA] intent={intent}" + (f" — {notes}" if notes else "")
        await self._request(
            "PATCH",
            f"/crm/leads/{contact_id}",
            json={
                "qualificado": True,
                "urgencia_venda": _PRIORITY_TO_URGENCIA[priority],
                "origem_mkt": "whatsapp-ia",
                "observacoes": await self._appended_observacoes(contact_id, note),
            },
        )

    async def get_appointment(self, appointment_id: str) -> Appointment | None:
        try:
            lead = await self._get_lead(appointment_id)
        except TrivusError:
            return None
        return self._to_appointment(lead)

    async def get_scheduled_appointments(self, day: date) -> list[Appointment]:
        leads: list[TrivusLead] = []
        page = 1
        total: int | None = None
        while total is None or (page - 1) * _PAGE_SIZE < total:
            resp = await self._request(
                "GET",
                "/agenda",
                params={
                    "store_id": self._store_id,
                    "apply_to": "agendamento",
                    "preset": "custom",
                    "from": day.isoformat(),
                    "to": day.isoformat(),
                    "page": page,
                    "page_size": _PAGE_SIZE,
                },
            )
            parsed = TrivusAgendaPage.model_validate(resp.json())
            leads.extend(parsed.items)
            total = parsed.total
            page += 1
            if not parsed.items:                 # guarda contra total inconsistente
                break
        out: list[Appointment] = []
        for lead in leads:
            appointment = self._to_appointment(lead)
            if appointment is not None:
                out.append(appointment)
        return out

    async def create_appointment(self, request: AppointmentRequest) -> Appointment:
        lead = await self._patch_agendamento(request.contact_id, request.start)
        appointment = self._to_appointment(lead)
        if appointment is None:
            raise TrivusError("agendamento não persistiu no trivus-api")
        return appointment.model_copy(update={"intent": request.intent})

    async def cancel_appointment(self, appointment_id: str) -> None:
        await self._request(
            "PATCH",
            f"/crm/leads/{appointment_id}/agendamento",
            json={"data_agendamento": None, "hora_agendamento": None},
        )

    async def reschedule_appointment(
        self, appointment_id: str, new_start: datetime
    ) -> Appointment:
        lead = await self._patch_agendamento(appointment_id, new_start)
        appointment = self._to_appointment(lead)
        if appointment is None:
            raise TrivusError("reagendamento não persistiu no trivus-api")
        return appointment

    async def create_handoff_task(self, task: HandoffTask) -> None:
        note = f"[IA→humano] motivo={task.reason.value} prioridade={task.priority.value}"
        if task.routing_hint:
            note += f" destino={task.routing_hint}"
        note += f"\n{task.context}"
        payload: dict[str, object] = {
            "observacoes": await self._appended_observacoes(task.contact_id, note)
        }
        if self._handoff_user_id:
            payload["assigned_to"] = self._handoff_user_id
        await self._request("PATCH", f"/crm/leads/{task.contact_id}", json=payload)

    # ---------- tradução (ACL) ----------

    async def _patch_agendamento(self, lead_id: str, start: datetime) -> TrivusLead:
        data, hora = to_trivus(start)
        resp = await self._request(
            "PATCH",
            f"/crm/leads/{lead_id}/agendamento",
            json={"data_agendamento": data, "hora_agendamento": hora},
        )
        return TrivusLead.model_validate(resp.json())

    def _to_contact(self, lead: TrivusLead) -> Contact:
        return Contact(
            id=lead.id,
            full_name=lead.nome or lead.telefone or lead.lid or "",
            phone=only_digits(lead.telefone or "") or (lead.lid or ""),
            intent=None,   # o Trivus não registra a intenção como conceito próprio
            priority=_URGENCIA_TO_PRIORITY.get(
                (lead.urgencia_venda or "").lower(), LeadPriority.MEDIUM
            ),
            notes=lead.observacoes,
        )

    def _to_appointment(self, lead: TrivusLead) -> Appointment | None:
        if not lead.data_agendamento or not lead.hora_agendamento:
            return None
        start = from_trivus(lead.data_agendamento, lead.hora_agendamento)
        # o Trivus não registra o serviço do agendamento → intent desconhecida;
        # a ficha usa shared_capacity para a ocupação contar mesmo assim.
        return Appointment(
            id=lead.id,
            contact_id=lead.id,
            intent="",
            start=start,
            end=start + timedelta(minutes=self._minutes),
        )
