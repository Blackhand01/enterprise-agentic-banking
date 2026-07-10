"""Emergency-fund goal defaults and date labels."""

from __future__ import annotations
from datetime import date, timedelta
from typing import Any


def default_emergency_fund_goal() -> dict[str, Any]:
    return {
        "goal_id": "emergency_fund",
        "description": "Raggiungere 10.000 EUR nel fondo emergenze entro 18 mesi.",
        "target_months": 18,
        "risk_preference": "balanced",
    }


default_user_goal = default_emergency_fund_goal


def add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    day = min(value.day, _days_in_month(year, month))
    return date(year, month, day)


def month_label(value: date) -> str:
    months = [
        "Gen",
        "Feb",
        "Mar",
        "Apr",
        "Mag",
        "Giu",
        "Lug",
        "Ago",
        "Set",
        "Ott",
        "Nov",
        "Dic",
    ]
    return f"{months[value.month - 1]} {value.year}"


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - timedelta(days=1)).day
