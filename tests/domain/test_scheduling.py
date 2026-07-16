"""Serviço de domínio de agenda — cálculo de slots (RN-10, RN-11)."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from agente.domain.crm import Appointment
from agente.domain.scheduling import available_slots, is_slot_available, slot_grid
from agente.domain.tenant import SchedulingPolicy, Service, WorkingHours

SP = ZoneInfo("America/Sao_Paulo")
MONDAY = date(2026, 7, 20)   # weekday() == 0
SUNDAY = date(2026, 7, 19)   # weekday() == 6


def _policy(*hours: WorkingHours, tz: str = "America/Sao_Paulo") -> SchedulingPolicy:
    return SchedulingPolicy(timezone=tz, working_hours=list(hours))


def _appt(intent: str, hour: int, minutes: int = 60) -> Appointment:
    start = datetime(MONDAY.year, MONDAY.month, MONDAY.day, hour, 0, tzinfo=SP)
    return Appointment(
        id=f"a{hour}",
        contact_id="c1",
        intent=intent,
        start=start,
        end=start + timedelta(minutes=minutes),
    )


def test_dates_are_the_expected_weekdays() -> None:
    # guarda: se estas datas mudarem de dia, o resto do arquivo mente.
    assert MONDAY.weekday() == 0
    assert SUNDAY.weekday() == 6


def test_60min_service_on_workday_yields_hourly_slots() -> None:
    policy = _policy(WorkingHours(weekday=0, open="09:00", close="18:00"))
    service = Service(name="Test", intent="x", duration_minutes=60)

    slots = slot_grid(policy, service, MONDAY)

    assert len(slots) == 9
    assert slots[0].start.hour == 9
    assert slots[0].start.tzinfo is not None      # RN-14
    assert slots[-1].start.hour == 17             # último slot 17:00–18:00
    assert slots[-1].end.hour == 18


def test_no_working_hours_for_the_day_yields_no_slots() -> None:
    policy = _policy(WorkingHours(weekday=0, open="09:00", close="18:00"))
    service = Service(name="Test", intent="x", duration_minutes=60)

    assert slot_grid(policy, service, SUNDAY) == []


def test_grid_step_follows_service_duration() -> None:
    # RN-11: a grade é do SERVIÇO — 45min → slots a cada 45min.
    policy = _policy(WorkingHours(weekday=0, open="09:00", close="12:00"))
    service = Service(name="Corte", intent="haircut", duration_minutes=45)

    slots = slot_grid(policy, service, MONDAY)

    starts = [(s.start.hour, s.start.minute) for s in slots]
    assert starts == [(9, 0), (9, 45), (10, 30), (11, 15)]  # 12:00 não cabe


def test_client_A_single_window_straight_through() -> None:
    # Cliente A: 08:00–16:00 direto, sem pausa.
    policy = _policy(WorkingHours(weekday=0, open="08:00", close="16:00"))
    service = Service(name="At", intent="x", duration_minutes=60)
    assert len(slot_grid(policy, service, MONDAY)) == 8


def test_client_B_split_window_with_lunch_break() -> None:
    # Cliente B: 06:00–12:00 e 16:00–18:00 (4h de almoço no meio).
    policy = _policy(
        WorkingHours(weekday=0, open="06:00", close="12:00"),
        WorkingHours(weekday=0, open="16:00", close="18:00"),
    )
    service = Service(name="At", intent="x", duration_minutes=60)

    hours = [s.start.hour for s in slot_grid(policy, service, MONDAY)]

    assert hours == [6, 7, 8, 9, 10, 11, 16, 17]   # nada entre 12h e 16h


def test_client_C_weekdays_differ_and_sunday_closed() -> None:
    # Cliente C: sábado só de manhã; domingo fechado (sem janela).
    policy = _policy(
        WorkingHours(weekday=5, open="09:00", close="12:00"),  # sábado
    )
    service = Service(name="At", intent="x", duration_minutes=60)

    saturday = date(2026, 7, 18)
    assert saturday.weekday() == 5
    assert len(slot_grid(policy, service, saturday)) == 3
    assert slot_grid(policy, service, SUNDAY) == []


# --- Tarefa 2.2: capacidade e ocupação ---

def _hourly_policy() -> SchedulingPolicy:
    return _policy(WorkingHours(weekday=0, open="09:00", close="18:00"))


def test_slot_available_while_below_capacity() -> None:
    # capacidade 3: dois ocupados às 10h → 10h ainda disponível.
    service = Service(name="At", intent="x", duration_minutes=60, capacity=3)
    busy = [_appt("x", 10), _appt("x", 10)]

    slots = available_slots(_hourly_policy(), service, MONDAY, busy)

    assert any(s.start.hour == 10 for s in slots)


def test_slot_full_at_capacity() -> None:
    # capacidade 3: três ocupados às 10h → 10h some.
    service = Service(name="At", intent="x", duration_minutes=60, capacity=3)
    busy = [_appt("x", 10), _appt("x", 10), _appt("x", 10)]

    slots = available_slots(_hourly_policy(), service, MONDAY, busy)

    assert all(s.start.hour != 10 for s in slots)


def test_capacity_counts_per_service_intent() -> None:
    # RN-11: uma manicure às 10h NÃO consome a vaga do corte.
    corte = Service(name="Corte", intent="haircut", duration_minutes=60, capacity=1)
    busy = [_appt("nails", 10)]   # ocupado é de OUTRO serviço

    slots = available_slots(_hourly_policy(), corte, MONDAY, busy)

    assert any(s.start.hour == 10 for s in slots)


def test_long_appointment_blocks_all_overlapping_slots() -> None:
    # Serviço de 90min às 10h ocupa 10h E 11h (capacidade 1).
    service = Service(name="At", intent="x", duration_minutes=60, capacity=1)
    busy = [_appt("x", 10, minutes=90)]   # 10:00–11:30

    slots = available_slots(_hourly_policy(), service, MONDAY, busy)

    blocked = {10, 11}
    assert all(s.start.hour not in blocked for s in slots)
    assert any(s.start.hour == 12 for s in slots)   # 12h livre


# --- Tarefa 2.3: antecedência mínima e "agora" (injetado) ---

def test_now_cutoff_hides_past_slots() -> None:
    service = Service(name="At", intent="x", duration_minutes=60)
    now = datetime(2026, 7, 20, 10, 30, tzinfo=SP)   # 10:30

    slots = available_slots(_hourly_policy(), service, MONDAY, [], now=now)

    assert all(s.start.hour != 10 for s in slots)   # 10h já passou
    assert slots[0].start.hour == 11                # 11h é o próximo


def test_min_notice_pushes_first_bookable_slot() -> None:
    # 2h de antecedência a partir de 10:30 → primeiro slot é 13h.
    service = Service(name="At", intent="x", duration_minutes=60)
    policy = SchedulingPolicy(
        timezone="America/Sao_Paulo",
        min_notice_minutes=120,
        working_hours=[WorkingHours(weekday=0, open="09:00", close="18:00")],
    )
    now = datetime(2026, 7, 20, 10, 30, tzinfo=SP)

    slots = available_slots(policy, service, MONDAY, [], now=now)

    assert slots[0].start.hour == 13


def test_now_cutoff_respects_store_timezone() -> None:
    # now em UTC (13:30Z == 10:30 em SP). O corte deve usar o fuso da loja.
    service = Service(name="At", intent="x", duration_minutes=60)
    now_utc = datetime(2026, 7, 20, 13, 30, tzinfo=ZoneInfo("UTC"))

    slots = available_slots(_hourly_policy(), service, MONDAY, [], now=now_utc)

    assert slots[0].start.hour == 11   # mesmo resultado do teste em SP


# --- Tarefa 2.4: validação de um slot específico (base do RN-13) ---

def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(MONDAY.year, MONDAY.month, MONDAY.day, hour, minute, tzinfo=SP)


def test_is_slot_available_true_for_free_grid_slot() -> None:
    service = Service(name="At", intent="x", duration_minutes=60, capacity=1)
    assert is_slot_available(_hourly_policy(), service, _at(11), [], now=_at(9)) is True


def test_is_slot_available_false_when_at_capacity() -> None:
    service = Service(name="At", intent="x", duration_minutes=60, capacity=1)
    busy = [_appt("x", 11)]
    assert is_slot_available(_hourly_policy(), service, _at(11), busy, now=_at(9)) is False


def test_is_slot_available_false_in_the_past() -> None:
    service = Service(name="At", intent="x", duration_minutes=60)
    assert is_slot_available(_hourly_policy(), service, _at(9), [], now=_at(10)) is False


def test_is_slot_available_false_when_not_on_grid() -> None:
    # 10:30 não é início de slot numa grade horária.
    service = Service(name="At", intent="x", duration_minutes=60)
    assert is_slot_available(_hourly_policy(), service, _at(10, 30), [], now=_at(9)) is False


# --- Capacidade compartilhada da LOJA (caso revenda; adapter Trivus não sabe o serviço) ---

def test_shared_capacity_counts_all_intents() -> None:
    policy = SchedulingPolicy(
        timezone="America/Sao_Paulo",
        shared_capacity=True,
        working_hours=[WorkingHours(weekday=0, open="09:00", close="18:00")],
    )
    buy = Service(name="Comprar", intent="buy_vehicle", duration_minutes=60, capacity=3)
    # 3 ocupados às 10h, de intents variadas (inclusive desconhecida "")
    busy = [_appt("buy_vehicle", 10), _appt("sell_vehicle", 10), _appt("", 10)]

    slots = available_slots(policy, buy, MONDAY, busy)

    assert all(s.start.hour != 10 for s in slots)   # capacidade é da LOJA: 3/3 ocupado
    assert any(s.start.hour == 11 for s in slots)
