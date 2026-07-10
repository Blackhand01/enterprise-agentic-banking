"""Support primitives for the provider-agnostic banking agent."""

from __future__ import annotations
import calendar
import json
import re
from pathlib import Path
from typing import Any, Callable, ClassVar, Protocol

try:
    from .guardrails import filter_active_policies
    from .llm_provider import (
        LLMProviderConfig,
        build_chat_client,
        build_chat_client_for_config,
        fallback_provider_configs,
    )
except ImportError:
    from guardrails import filter_active_policies
    from llm_provider import (
        LLMProviderConfig,
        build_chat_client,
        build_chat_client_for_config,
        fallback_provider_configs,
    )


class RetrievalQueryTranslator:
    """LLM-backed zero-shot translator for semantic retrieval queries."""

    _cache: ClassVar[dict[str, str]] = {}
    _override: ClassVar[Callable[[str], str] | None] = None

    @classmethod
    def set_override(cls, translator: Callable[[str], str] | None) -> None:
        cls._override = translator
        cls._cache = {}

    @classmethod
    def translate(cls, query: str) -> str:
        normalized = query.strip()
        if not normalized:
            return normalized
        if cls._override is not None:
            return cls._override(normalized).strip() or normalized
        cache_key = normalized.lower()
        if cache_key in cls._cache:
            return cls._cache[cache_key]
        response = cls._translate_with_configured_provider(normalized)
        translated = (response.choices[0].message.content or "").strip()
        translated = _clean_translation(translated) or normalized
        cls._cache[cache_key] = translated
        return translated

    @staticmethod
    def _translation_messages(query: str) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "Translate the user's short semantic retrieval query to English for "
                    "a bank transaction search about customer purchases, merchants and activities. "
                    "Resolve ambiguous terms using that transaction-search context. "
                    "Return only the translated search phrase, with no explanation."
                ),
            },
            {"role": "user", "content": query},
        ]

    @classmethod
    def _translate_with_configured_provider(cls, query: str):
        client, primary_config = build_chat_client()
        kwargs = {
            "model": primary_config.model,
            "messages": cls._translation_messages(query),
            "temperature": 0,
            "max_tokens": 24,
        }
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as exc:
            return cls._translate_with_fallbacks(
                kwargs=kwargs,
                primary_config=primary_config,
                original_error=exc,
            )

    @staticmethod
    def _translate_with_fallbacks(
        *,
        kwargs: dict,
        primary_config: LLMProviderConfig,
        original_error: Exception,
    ):
        if not _is_retryable_provider_error(original_error):
            raise original_error
        errors = [f"{primary_config.provider}: {original_error}"]
        for config in fallback_provider_configs(primary_config):
            fallback_kwargs = dict(kwargs)
            fallback_kwargs["model"] = config.model
            try:
                client = build_chat_client_for_config(config)
                return client.chat.completions.create(**fallback_kwargs)
            except Exception as exc:
                errors.append(f"{config.provider}: {exc}")
                continue
        raise RuntimeError(
            "All configured LLM providers failed during retrieval query translation: "
            + " | ".join(errors)
        )


def _clean_translation(value: str) -> str:
    return value.replace("\n", " ").strip().strip('"').strip("'").strip()


def _is_retryable_provider_error(error: Exception) -> bool:
    lowered = str(error).lower()
    return any(
        marker in lowered
        for marker in (
            "401",
            "403",
            "408",
            "409",
            "429",
            "500",
            "502",
            "503",
            "504",
            "invalid_api_key",
            "rate_limit",
            "rate limit",
            "timeout",
            "temporarily unavailable",
            "service unavailable",
        )
    )


class SlidingWindowChatHistory:
    """Stores only the most recent messages needed for the agent context."""

    def __init__(self, window_size: int = 10) -> None:
        self.window_size = window_size
        self._messages: list[dict[str, Any]] = []

    @property
    def messages(self) -> list[dict[str, Any]]:
        return list(self._messages)

    def append(self, message: dict[str, Any]) -> None:
        self._messages.append(message)
        self._messages = self._messages[-self.window_size :]

    def extend(self, messages: list[dict[str, Any]]) -> None:
        for message in messages:
            self.append(message)


class PolicyLookup(Protocol):
    def get_policies_by_category(self, category: str) -> str: ...


def build_system_prompt(policy_retriever: PolicyLookup) -> str:
    """Build the system prompt with active, non-stale policies injected."""
    transfer_policy = policy_retriever.get_policies_by_category(
        "payments_and_transfers"
    )
    grounding_policy = policy_retriever.get_policies_by_category("grounding")
    return f"""
            Sei il TCS Agentic Bank Assistant.

            Il tuo compito:
            - Comprendere la richiesta del cliente.
            - Usare le funzioni disponibili quando la risposta dipende da dati conto, transazioni, policy o azioni bancarie.
            - Recuperare il contesto rilevante prima di dare consigli finanziari o proporre un'operazione.
            - Produrre risposte chiare per il cliente con fatti, razionale e prossimo passo proposto.
            - Non inventare mai saldi, transazioni, beneficiari, policy o risultati di esecuzione.
            - Se un dato richiesto non è disponibile nel profilo corrente, dichiaralo in modo conciso e fermati.
            - Se un'operazione non può essere completata, spiega solo il prossimo passo lato cliente. Non discutere dettagli implementativi.
            - Non dire mai che il denaro è stato spostato se il risultato di una funzione non conferma l'operazione.

            Regole di conversazione cliente:
            - Parla sempre in italiano.
            - Non mostrare mai nomi di funzioni, chiamate tool, tag tipo <function=...>, ID policy, ID documento o dettagli tecnici interni.
            - Non inventare funzioni non disponibili. Se uno strumento non esiste, non citarlo.
            - Quando il cliente chiede saldi, totale disponibile, conti, spese pianificate o quadro complessivo, recupera prima il contesto verificato con gli strumenti disponibili.
            - Quando il cliente interroga lo storico, usa gli strumenti disponibili per recuperare dati verificati invece di rispondere a memoria.
            - Se uno strumento restituisce transazioni, rispondi che il dato è stato trovato e riassumi solo quelle transazioni. Non dire che il dato manca.
            - Se uno strumento restituisce NO_DATA, rispondi con una sola frase concisa. Non aggiungere offerte generiche di aiuto.
            - Se il cliente chiede cos'è un merchant, descrivi solo cosa risulta nel profilo cliente: data, importo, categoria e nome merchant. Non inferire il tipo di azienda oltre i dati disponibili.
            - Quando il cliente chiede cosa puoi fare, descrivi solo capability realmente supportate: consultare saldi e contesto cliente, analizzare transazioni per categoria, spiegare proposte, preparare trasferimenti verso destinazioni supportate con controlli di sicurezza.
            - Se il cliente chiede dati di altri clienti o di tutti gli account della banca, rifiuta in modo breve e spiega che puoi usare solo il suo contesto bancario verificato.

            Strict Compliance Rule:
            - Se il cliente chiede informazioni finanziarie o prodotti non presenti nel contesto recuperato, ad esempio mutui, prestiti, linee di credito o prodotti non caricati, devi dichiarare esplicitamente che il dato manca.
            - Non offrire calcoli manuali di rischio.
            - Non chiedere al cliente di fornire manualmente i dati mancanti.
            - Non offrire consulenza finanziaria generale.
            - Per dati mancanti usa questo formato esatto: "Non ho accesso ai dati relativi a [argomento] nel tuo profilo attuale."

            Policy trasferimenti attiva:
            {transfer_policy}

            Policy grounding attiva:
            {grounding_policy}
        """.strip()


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
            raise ValueError(
                f"Invalid JSON in policy database: {self.db_path}"
            ) from exc
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


_ITALIAN_MONTHS = {
    "gennaio": 1,
    "febbraio": 2,
    "marzo": 3,
    "aprile": 4,
    "maggio": 5,
    "giugno": 6,
    "luglio": 7,
    "agosto": 8,
    "settembre": 9,
    "ottobre": 10,
    "novembre": 11,
    "dicembre": 12,
}


def _extract_month_range(text: str) -> tuple[str, str] | None:
    lowered = text.lower()
    match = re.search(
        r"\b(" + "|".join(_ITALIAN_MONTHS) + r")\s+(\d{4})\b",
        lowered,
    )
    if not match:
        return None
    month = _ITALIAN_MONTHS[match.group(1)]
    year = int(match.group(2))
    last_day = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"


def _is_temporal_follow_up(text: str) -> bool:
    lowered = text.strip().lower()
    if not lowered:
        return False
    month_pattern = "|".join(_ITALIAN_MONTHS)
    return bool(
        re.fullmatch(
            r"(e\s+)?(a|nel|in)?\s*(" + month_pattern + r")\s+\d{4}\s*\??", lowered
        )
    )
