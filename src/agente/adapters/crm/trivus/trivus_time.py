"""Tradução de tempo (RN-62): tz-aware (domínio) ↔ naïve Brasília (Trivus)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

SP = ZoneInfo("America/Sao_Paulo")


def to_trivus(dt: datetime) -> tuple[str, str]:
    """datetime tz-aware → ("YYYY-MM-DD", "HH:MM") no fuso da loja."""
    local = dt.astimezone(SP)
    return local.date().isoformat(), local.strftime("%H:%M")


def from_trivus(data: date, hora: str) -> datetime:
    """date + "HH:MM"/"HH:MM:SS" naïve Brasília → datetime tz-aware."""
    hour, minute = int(hora[0:2]), int(hora[3:5])
    return datetime(data.year, data.month, data.day, hour, minute, tzinfo=SP)
