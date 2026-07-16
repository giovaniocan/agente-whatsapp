"""TrivusCRM contra fixtures REAIS (Plano 08) — HTTP mockado com respx."""

import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest
import respx
from pydantic import ValidationError

from agente.adapters.crm.trivus import FeatureLockedError, TrivusCRM, TrivusError
from agente.adapters.crm.trivus.dtos import TrivusLead
from agente.adapters.crm.trivus.trivus_time import from_trivus, to_trivus
from agente.domain.crm import AppointmentRequest, HandoffTask
from agente.domain.enums import EscalationTrigger, LeadPriority
from agente.domain.tenant import CRMConfig

FIX = Path(__file__).parent / "fixtures"
SP = ZoneInfo("America/Sao_Paulo")
BASE = "https://api.test"
LEAD_ID = "29d737a0-78ea-4421-9b12-3a084cdeb8fe"


def _fx(name: str) -> object:
    return json.loads((FIX / name).read_text())


def _crm(**settings_over: str) -> TrivusCRM:
    settings = {
        "store_id": "11fc7e9a-ccec-4ceb-b4e1-4e821e473e67",
        "email": "ia@exemplo.com.br",
    }
    settings.update(settings_over)
    return TrivusCRM(
        CRMConfig(type="trivus", base_url=BASE, api_key="senha-teste", settings=settings)
    )


def _login_route() -> respx.Route:
    return respx.post(f"{BASE}/auth/login").mock(
        return_value=httpx.Response(200, json=_fx("login.json"))
    )


# ---------- 8.1 DTOs ----------

def test_dtos_parse_real_fixtures() -> None:
    lead = TrivusLead.model_validate(_fx("lead_full.json"))
    assert lead.data_agendamento == date(2026, 7, 7)
    assert lead.hora_agendamento == "17:00"
    TrivusLead.model_validate(_fx("lead_created.json"))    # criado (quase tudo null)


def test_dto_missing_required_field_fails() -> None:
    broken = dict(_fx("lead_full.json"))  # type: ignore[arg-type]
    broken.pop("id")
    with pytest.raises(ValidationError):
        TrivusLead.model_validate(broken)


# ---------- 8.3 tempo ----------

def test_time_roundtrip_and_both_hour_formats() -> None:
    assert to_trivus(datetime(2026, 7, 20, 14, 30, tzinfo=SP)) == ("2026-07-20", "14:30")
    assert from_trivus(date(2026, 7, 7), "17:00") == datetime(2026, 7, 7, 17, 0, tzinfo=SP)
    assert from_trivus(date(2026, 7, 7), "14:30:00").minute == 30


def test_time_utc_day_crossing_keeps_local_date() -> None:
    utc = datetime(2026, 7, 21, 2, 30, tzinfo=ZoneInfo("UTC"))   # 23:30 do dia 20 em SP
    assert to_trivus(utc) == ("2026-07-20", "23:30")


# ---------- 8.2 auth + erros ----------

@respx.mock
async def test_login_once_and_bearer_header() -> None:
    login = _login_route()
    leads = respx.get(f"{BASE}/crm/leads").mock(return_value=httpx.Response(200, json=[]))
    crm = _crm()

    await crm.find_contact_by_phone("11936849133")
    await crm.find_contact_by_phone("11936849133")

    assert login.call_count == 1                           # token cacheado (JWT 7d)
    auth = leads.calls.last.request.headers["Authorization"]
    assert auth == "Bearer jwt-redigido-token-1"


@respx.mock
async def test_relogin_once_on_401() -> None:
    login = _login_route()
    respx.get(f"{BASE}/crm/leads").mock(
        side_effect=[
            httpx.Response(401, json={"error": "Token ausente"}),
            httpx.Response(200, json=[]),
        ]
    )
    assert await _crm().find_contact_by_phone("11936849133") is None
    assert login.call_count == 2                           # re-login UMA vez (RN-64)


@respx.mock
async def test_feature_locked_raises_specific_error() -> None:
    _login_route()
    respx.get(f"{BASE}/agenda").mock(
        return_value=httpx.Response(
            403, json={"error": "feature_locked", "feature_key": "agenda"}
        )
    )
    with pytest.raises(FeatureLockedError):
        await _crm().get_scheduled_appointments(date(2026, 7, 16))


@respx.mock
async def test_422_fastapi_shape_becomes_clear_error() -> None:
    _login_route()
    respx.get(f"{BASE}/crm/funnels").mock(
        return_value=httpx.Response(200, json=_fx("funnels.json"))
    )
    respx.post(f"{BASE}/crm/leads").mock(
        return_value=httpx.Response(
            422,
            json={"detail": [{"type": "missing", "loc": ["body", "store_id"],
                              "msg": "Field required"}]},
        )
    )
    with pytest.raises(TrivusError, match="422"):
        await _crm().create_contact("X", "11912345678")


# ---------- 8.4 métodos ----------

@respx.mock
async def test_find_by_phone_matches_ninth_digit_variant() -> None:
    _login_route()
    respx.get(f"{BASE}/crm/leads").mock(
        return_value=httpx.Response(
            200, json=[_fx("lead_full.json"), _fx("lead_created.json")]
        )
    )
    crm = _crm()

    found = await crm.find_contact_by_phone("1136849133")   # SEM o 9º dígito

    assert found is not None and found.id == LEAD_ID
    assert found.priority is LeadPriority.HIGH              # urgencia "alta"
    assert await crm.find_contact_by_phone("99999999999") is None


@respx.mock
async def test_create_contact_resolves_and_caches_initial_stage() -> None:
    _login_route()
    funnels = respx.get(f"{BASE}/crm/funnels").mock(
        return_value=httpx.Response(200, json=_fx("funnels.json"))
    )
    created = respx.post(f"{BASE}/crm/leads").mock(
        return_value=httpx.Response(201, json=_fx("lead_created.json"))
    )
    crm = _crm()

    contact = await crm.create_contact("Teste Agente", "(11) 91234-5678")
    await crm.create_contact("Outro", "(11) 98888-7777")

    assert contact.full_name == "Teste Agente"
    assert funnels.call_count == 1                          # stage CACHEADO
    body = json.loads(created.calls[0].request.content)
    assert body["stage_id"] == "037ec391-0000-0000-0000-000000000001"   # RECEBIDOS
    assert body["funil"] == "receptivo"


@respx.mock
async def test_qualification_appends_observacoes() -> None:
    _login_route()
    respx.get(f"{BASE}/crm/leads").mock(
        return_value=httpx.Response(200, json=[_fx("lead_full.json")])
    )
    patch = respx.patch(f"{BASE}/crm/leads/{LEAD_ID}").mock(
        return_value=httpx.Response(200, json=_fx("lead_full.json"))
    )

    await _crm().update_lead_qualification(
        LEAD_ID, intent="buy_vehicle", priority=LeadPriority.HIGH, notes="quer SUV"
    )

    body = json.loads(patch.calls.last.request.content)
    assert body["qualificado"] is True
    assert body["urgencia_venda"] == "alta"
    assert body["observacoes"].startswith("Interesse em troca com entrada.")  # preservou
    assert "intent=buy_vehicle" in body["observacoes"]
    assert "quer SUV" in body["observacoes"]


@respx.mock
async def test_agenda_paginates_until_total() -> None:
    _login_route()
    page1 = {"items": [_fx("lead_full.json")], "total": 101, "page": 1}
    page2 = {"items": [], "total": 101, "page": 2}
    agenda = respx.get(f"{BASE}/agenda").mock(
        side_effect=[httpx.Response(200, json=page1), httpx.Response(200, json=page2)]
    )

    appts = await _crm().get_scheduled_appointments(date(2026, 7, 7))

    assert agenda.call_count == 2                           # paginou até o total
    assert len(appts) == 1
    assert appts[0].start == datetime(2026, 7, 7, 17, 0, tzinfo=SP)
    assert appts[0].end == datetime(2026, 7, 7, 18, 0, tzinfo=SP)   # 60min default


@respx.mock
async def test_schedule_cancel_reschedule_bodies() -> None:
    _login_route()
    ag = respx.patch(f"{BASE}/crm/leads/{LEAD_ID}/agendamento").mock(
        return_value=httpx.Response(200, json=_fx("lead_full.json"))
    )
    crm = _crm()

    await crm.create_appointment(
        AppointmentRequest(
            contact_id=LEAD_ID,
            intent="buy_vehicle",
            start=datetime(2026, 7, 20, 14, 30, tzinfo=SP),
            end=datetime(2026, 7, 20, 15, 30, tzinfo=SP),
        )
    )
    assert json.loads(ag.calls[0].request.content) == {
        "data_agendamento": "2026-07-20", "hora_agendamento": "14:30"
    }

    await crm.cancel_appointment(LEAD_ID)
    assert json.loads(ag.calls[1].request.content) == {
        "data_agendamento": None, "hora_agendamento": None
    }

    moved = await crm.reschedule_appointment(
        LEAD_ID, datetime(2026, 7, 22, 9, 0, tzinfo=SP)
    )
    assert json.loads(ag.calls[2].request.content) == {
        "data_agendamento": "2026-07-22", "hora_agendamento": "09:00"
    }
    assert moved.id == LEAD_ID


@respx.mock
async def test_get_appointment_by_id_and_unknown() -> None:
    _login_route()
    respx.get(f"{BASE}/crm/leads").mock(
        return_value=httpx.Response(200, json=[_fx("lead_full.json")])
    )
    crm = _crm()

    appt = await crm.get_appointment(LEAD_ID)
    assert appt is not None and appt.start.hour == 17
    assert await crm.get_appointment("nao-existe") is None


@respx.mock
async def test_handoff_assigns_and_appends_context() -> None:
    _login_route()
    respx.get(f"{BASE}/crm/leads").mock(
        return_value=httpx.Response(200, json=[_fx("lead_full.json")])
    )
    patch = respx.patch(f"{BASE}/crm/leads/{LEAD_ID}").mock(
        return_value=httpx.Response(200, json=_fx("lead_full.json"))
    )

    await _crm(handoff_user_id="u-humano-9").create_handoff_task(
        HandoffTask(
            contact_id=LEAD_ID,
            reason=EscalationTrigger.EXPLICIT_REQUEST,
            priority=LeadPriority.HIGH,
            context="resumo do papo",
        )
    )

    body = json.loads(patch.calls.last.request.content)
    assert body["assigned_to"] == "u-humano-9"
    assert body["observacoes"].startswith("Interesse em troca com entrada.")
    assert "[IA→humano]" in body["observacoes"]
    assert "resumo do papo" in body["observacoes"]


# ---------- RN-60: vocabulário Trivus preso neste pacote ----------

def test_no_trivus_vocabulary_outside_adapter() -> None:
    src = Path(__file__).resolve().parents[3] / "src" / "agente"
    tokens = ("data_agendamento", "hora_agendamento", "urgencia_venda", "agendado_por")
    offenders: list[str] = []
    for path in src.rglob("*.py"):
        if "adapters/crm/trivus" in str(path):
            continue
        text = path.read_text()
        offenders += [f"{path.name}:{token}" for token in tokens if token in text]
    assert offenders == []
