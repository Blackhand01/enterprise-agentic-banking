"""Centralized Pydantic schemas for OpenAI-compatible agent tool contracts.

The agent exposes these schemas to the selected LLM provider for tool calling
and uses the same models to validate tool arguments before executing local
Python functions.
"""

from __future__ import annotations
import re
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FetchTransactionsArgs(BaseModel):
    """Arguments for the fetch_transactions tool."""

    model_config = ConfigDict(extra="forbid")
    category: str | None = Field(
        default=None,
        description=(
            "Macro-categoria bancaria, se il cliente la indica. Lascia vuoto "
            "quando la ricerca è concettuale."
        ),
    )
    search_query: str | None = Field(
        default=None,
        description=(
            "Frase naturale o concetto semantico cercato dal cliente. Preferisci "
            "la porzione completa della richiesta cliente rispetto a token isolati, "
            "così il backend può risolvere ambiguità tramite embedding search locale."
        ),
    )
    date_from: str | None = Field(
        default=None,
        description="Data iniziale opzionale in formato YYYY-MM-DD.",
    )
    date_to: str | None = Field(
        default=None,
        description="Data finale opzionale in formato YYYY-MM-DD.",
    )

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None

    @field_validator("search_query")
    @classmethod
    def normalize_search_query(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None

    @field_validator("date_from", "date_to")
    @classmethod
    def normalize_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
            raise ValueError("date filters must use YYYY-MM-DD")
        return normalized

    @model_validator(mode="after")
    def require_category_or_search_query(self) -> "FetchTransactionsArgs":
        if not self.category and not self.search_query:
            raise ValueError("category or search_query is required")
        return self


class NoArgs(BaseModel):
    """Empty argument contract for read-only tools without parameters."""

    model_config = ConfigDict(extra="forbid")


class ExecuteTransferArgs(BaseModel):
    """Arguments for the execute_transfer tool."""

    model_config = ConfigDict(extra="forbid")
    recipient: str = Field(
        ...,
        min_length=1,
        description="Beneficiario del trasferimento o nome del saving pot.",
    )
    amount: float = Field(
        ...,
        gt=0,
        description="Importo in EUR.",
    )
    operation_id: str | None = Field(
        default=None,
        description="Identificativo idempotente dell'operazione, se disponibile.",
    )

    @field_validator("recipient")
    @classmethod
    def normalize_recipient(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("recipient cannot be blank")
        return normalized

    @field_validator("operation_id")
    @classmethod
    def normalize_operation_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


TOOL_ARG_MODELS: dict[str, type[BaseModel]] = {
    "get_balance_summary": NoArgs,
    "get_customer_context": NoArgs,
    "get_spending_summary": NoArgs,
    "fetch_transactions": FetchTransactionsArgs,
    "execute_transfer": ExecuteTransferArgs,
}


def llm_tool_definitions() -> list[dict[str, Any]]:
    """Return OpenAI-compatible tool definitions from the central Pydantic models."""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_balance_summary",
                "description": (
                    "Recupera dai sistemi bancari locali i conti del cliente, "
                    "i saldi e il saldo totale in EUR."
                ),
                "parameters": NoArgs.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_customer_context",
                "description": (
                    "Recupera il contesto cliente verificato: conti, saldi, "
                    "ultimo stipendio, pagamenti pianificati, transazioni recenti "
                    "e storico mensile."
                ),
                "parameters": NoArgs.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_spending_summary",
                "description": (
                    "Calcola in modo deterministico il totale delle uscite recenti "
                    "del cliente usando solo transazioni con importo negativo."
                ),
                "parameters": NoArgs.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_transactions",
                "description": (
                    "Recupera lo storico delle transazioni bancarie del cliente. "
                    "Consente di filtrare per macro-categoria o di effettuare "
                    "ricerche semantiche su concetti specifici tramite embedding. "
                    "Supporta filtri temporali strutturati con date_from e date_to."
                ),
                "parameters": FetchTransactionsArgs.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "execute_transfer",
                "description": "Invia una richiesta di trasferimento verso un beneficiario o saving pot.",
                "parameters": ExecuteTransferArgs.model_json_schema(),
            },
        },
    ]


def groq_tool_definitions() -> list[dict[str, Any]]:
    """Backward-compatible alias kept for older imports/tests."""
    return llm_tool_definitions()


def validate_tool_arguments(tool_name: str, arguments: dict[str, Any]) -> BaseModel:
    """Validate raw tool-call arguments against the matching Pydantic model."""
    model = TOOL_ARG_MODELS.get(tool_name)
    if model is None:
        raise ValueError(f"Unknown tool: {tool_name}")
    return model.model_validate(arguments)
