"""Fixed customer goal used by the Part A emergency-fund prototype."""

from __future__ import annotations

from typing import Any


def default_emergency_fund_goal() -> dict[str, Any]:
    return {
        "goal_id": "emergency_fund",
        "description": "Raggiungere 10.000 EUR nel fondo emergenze entro 18 mesi.",
        "target_months": 18,
        "risk_preference": "balanced",
    }


default_user_goal = default_emergency_fund_goal
