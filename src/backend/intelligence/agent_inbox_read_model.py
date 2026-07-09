"""Agent inbox read model for proactive recommendations."""

from __future__ import annotations

from typing import Any


def build_agent_inbox_items(proposal: dict[str, Any]) -> list[dict[str, Any]]:
    status = "completed" if proposal.get("already_executed") else "pending_approval"
    if proposal["route"] == "BLOCKED":
        status = "blocked"

    return [
        {
            "id": proposal["proposal_id"],
            "title": proposal["title"],
            "summary": proposal["recommended_action"],
            "status": status,
            "route": proposal["route"],
            "required_next_step": proposal["required_next_step"],
            "evidence": {
                "known_expenses_30d": proposal["upcoming_expenses_30d"],
                "projected_checking_balance": proposal["projected_checking_balance"],
                "projected_emergency_balance": proposal["projected_emergency_balance"],
            },
        }
    ]
