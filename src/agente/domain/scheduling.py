"""
Serviço de domínio de agenda (DDD): calcula horários livres.

Puro, zero I/O (RN-10): recebe a política do tenant + serviço + dia (e, adiante,
os ocupados) e devolve slots. A função NÃO conhece "almoço" — apenas soma as
janelas de `working_hours`; um intervalo no meio do dia é só a ausência de janela.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from agente.domain.crm import Appointment, AvailableSlot
from agente.domain.tenant import SchedulingPolicy, Service, WorkingHours


def _parse_hhmm(value: str) -> time:
    hh, mm = value.split(":")
    return time(int(hh), int(mm))


def _windows_for_day(policy: SchedulingPolicy, day: date) -> list[WorkingHours]:
    return [w for w in policy.working_hours if w.weekday == day.weekday()]


def slot_grid(policy: SchedulingPolicy, service: Service, day: date) -> list[AvailableSlot]:
    """Grade de slots do dia para um serviço, pela sua duração (RN-11)."""
    tz = ZoneInfo(policy.timezone)
    step = timedelta(minutes=service.duration_minutes)
    slots: list[AvailableSlot] = []

    for window in _windows_for_day(policy, day):
        cursor = datetime.combine(day, _parse_hhmm(window.open), tzinfo=tz)
        window_end = datetime.combine(day, _parse_hhmm(window.close), tzinfo=tz)
        # Só cabe um slot se ele terminar dentro da janela.
        while cursor + step <= window_end:
            slots.append(AvailableSlot(start=cursor, end=cursor + step))
            cursor += step

    return slots


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def available_slots(
    policy: SchedulingPolicy,
    service: Service,
    day: date,
    busy: list[Appointment],
    now: datetime | None = None,
) -> list[AvailableSlot]:
    """
    Slots realmente livres = grade do dia menos os que já atingiram a capacidade
    e menos os que caem antes da antecedência mínima.

    A ocupação é casada POR SERVIÇO (RN-11): só contam agendamentos da mesma
    intent que se sobrepõem ao slot. `now` é INJETADO (RN-14): quando presente,
    o slot só vale se começar em `now + min_notice` ou depois — a comparação é
    tz-aware, então funciona com `now` em qualquer fuso.
    """
    same_service = [a for a in busy if a.intent == service.intent]
    earliest = (
        now + timedelta(minutes=policy.min_notice_minutes) if now is not None else None
    )
    free: list[AvailableSlot] = []

    for slot in slot_grid(policy, service, day):
        if earliest is not None and slot.start < earliest:
            continue
        taken = sum(
            1 for a in same_service if _overlaps(slot.start, slot.end, a.start, a.end)
        )
        if taken < service.capacity:
            free.append(slot)

    return free


def is_slot_available(
    policy: SchedulingPolicy,
    service: Service,
    start: datetime,
    busy: list[Appointment],
    now: datetime | None = None,
) -> bool:
    """
    True se `start` é um horário livre válido para o serviço (RN-13).

    Reusa `available_slots` — assim a validação do commit é idêntica à oferta
    feita ao cliente. `start` fora da grade, no passado ou lotado → False.
    """
    local_day = start.astimezone(ZoneInfo(policy.timezone)).date()
    return any(
        slot.start == start
        for slot in available_slots(policy, service, local_day, busy, now=now)
    )
