"""Centralized Pydantic schemas for agent tool contracts.

The agent exposes these schemas to Groq for tool calling and uses the same
models to validate tool arguments before executing local Python functions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FetchTransactionsArgs(BaseModel):
    """Arguments for the fetch_transactions tool."""

    model_config = ConfigDict(extra="forbid")

    category: str = Field(
        ...,
        min_length=1,
        description="Categoria transazione, ad esempio sport, bollette, stipendio.",
    )
    search_query: str | None = Field(
        default=None,
        description=(
            "Filtro testuale opzionale per merchant, descrizione, categoria o data. "
            "Esempi: ski, ProSki, running."
        ),
    )

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("category cannot be blank")
        return normalized

    @field_validator("search_query")
    @classmethod
    def normalize_search_query(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None


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
    "fetch_transactions": FetchTransactionsArgs,
    "execute_transfer": ExecuteTransferArgs,
}


def groq_tool_definitions() -> list[dict[str, Any]]:
    """Return Groq-compatible tool definitions from the central Pydantic models."""

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
                "name": "fetch_transactions",
                "description": "Recupera transazioni grounded dal ledger per categoria.",
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


def validate_tool_arguments(tool_name: str, arguments: dict[str, Any]) -> BaseModel:
    """Validate raw tool-call arguments against the matching Pydantic model."""

    model = TOOL_ARG_MODELS.get(tool_name)
    if model is None:
        raise ValueError(f"Unknown tool: {tool_name}")
    return model.model_validate(arguments)
