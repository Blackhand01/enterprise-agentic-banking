"""Policy retrieval layer for the Agentic Banking prototype.

This module is intentionally small and deterministic. Its job is to load the
mock policy database and ensure stale policies never reach the LLM context.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .guardrails import filter_active_policies
except ImportError:  # Allows direct script-style imports during prototyping.
    from guardrails import filter_active_policies


class PolicyRetriever:
    """Loads active bank policies and formats them for prompt grounding."""

    def __init__(self, db_path: str | Path = "policyDB.json") -> None:
        self.db_path = Path(db_path)
        self._policies = self._load_active_policies()

    def _load_active_policies(self) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Policy database not found: {self.db_path}")

        try:
            raw = json.loads(self.db_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in policy database: {self.db_path}") from exc

        if not isinstance(raw, list):
            raise ValueError("Policy database must be a list of policy objects.")

        return filter_active_policies(raw)

    def get_policies_by_category(self, category: str) -> str:
        """Return active policies for a category as prompt-ready text."""

        normalized_category = category.strip().lower()
        matches = [
            policy
            for policy in self._policies
            if str(policy.get("category", "")).strip().lower() == normalized_category
        ]

        if not matches:
            return f"Nessuna policy attiva trovata per categoria: {category}"

        formatted: list[str] = []
        for policy in matches:
            policy_id = policy.get("id", "unknown_policy")
            title = policy.get("title", policy_id)
            version = policy.get("version", "unspecified")
            body = policy.get("body", "")

            formatted.append(
                "\n".join(
                    [
                        f"Policy ID: {policy_id}",
                        f"Titolo: {title}",
                        f"Categoria: {policy.get('category', category)}",
                        f"Versione: {version}",
                        f"Corpo: {body}",
                    ]
                )
            )

        return "\n\n---\n\n".join(formatted)
