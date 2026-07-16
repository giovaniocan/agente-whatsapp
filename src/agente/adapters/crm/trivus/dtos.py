"""
DTOs da fronteira com o trivus-api — PRIVADOS deste pacote (RN-60).

Validados contra fixtures reais (RN-61): campo obrigatório ausente/ inválido →
erro claro; campos extras são tolerados (a API pode evoluir sem nos quebrar).
"""

from datetime import date

from pydantic import BaseModel


class TrivusLogin(BaseModel):
    access_token: str


class TrivusStage(BaseModel):
    id: str
    name: str
    sort_order: int


class TrivusFunnel(BaseModel):
    id: str
    name: str
    stages: list[TrivusStage] = []


class TrivusLead(BaseModel):
    id: str
    store_id: str | None = None
    stage_id: str | None = None
    nome: str | None = None
    telefone: str | None = None
    lid: str | None = None
    qualificado: bool | None = None
    urgencia_venda: str | None = None
    observacoes: str | None = None
    assigned_to: str | None = None
    data_agendamento: date | None = None
    hora_agendamento: str | None = None     # "HH:MM" no GET, "HH:MM:SS" no PATCH
    created_at: str | None = None           # UTC ISO — ordenável lexicograficamente


class TrivusAgendaPage(BaseModel):
    items: list[TrivusLead]
    total: int
    page: int
