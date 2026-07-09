"""Pure embedding-based semantic retrieval for customer transactions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

import numpy as np


DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_SIMILARITY_THRESHOLD = 0.4


@dataclass(frozen=True)
class TransactionSearchResult:
    """A transaction paired with its cosine-similarity score."""

    transaction: dict[str, Any]
    score: float


class SemanticTransactionRetriever:
    """Searches transactions exclusively via SentenceTransformer embeddings."""

    _model_cache: ClassVar[dict[str, Any]] = {}

    def __init__(
        self,
        transactions: list[dict[str, Any]],
        *,
        model_name: str = DEFAULT_MODEL_NAME,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> None:
        self.transactions = transactions
        self.model_name = model_name
        self.threshold = threshold
        self.model = self._load_model(model_name)
        self.documents = [_transaction_document(transaction) for transaction in transactions]
        self.embeddings = self._embed_texts(self.documents)

    def semantic_search(
        self,
        search_query: str | None,
        *,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return transaction dictionaries sorted by embedding similarity."""

        if not search_query:
            return self.transactions[: limit or len(self.transactions)]
        if not self.transactions:
            return []

        query_embedding = self._embed_texts([search_query])[0]
        scores = _cosine_scores(query_embedding, self.embeddings)
        ranked = [
            TransactionSearchResult(
                transaction=self.transactions[index],
                score=float(score),
            )
            for index, score in enumerate(scores)
            if float(score) >= self.threshold
        ]
        ranked.sort(key=lambda result: result.score, reverse=True)
        if limit is not None:
            ranked = ranked[:limit]

        return [
            {
                **result.transaction,
                "semantic_score": round(result.score, 4),
            }
            for result in ranked
        ]

    @classmethod
    def _load_model(cls, model_name: str) -> Any:
        if model_name not in cls._model_cache:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is required for SemanticTransactionRetriever. "
                    "Install dependencies with: python3 -m pip install -r requirements.txt"
                ) from exc

            cls._model_cache[model_name] = SentenceTransformer(model_name)
        return cls._model_cache[model_name]

    def _embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=np.float32)

        vectors = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=False,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)


def _transaction_document(transaction: dict[str, Any]) -> str:
    """Build a semantic document only from fields present in the ledger."""

    fields = [
        ("merchant", transaction.get("merchant")),
        ("display_name", transaction.get("display_name")),
        ("category", transaction.get("category")),
        ("date", transaction.get("date")),
        ("direction", transaction.get("direction")),
        ("amount", transaction.get("amount")),
    ]
    return ". ".join(
        f"{label}: {value}"
        for label, value in fields
        if value is not None and str(value).strip()
    )


def _cosine_scores(query: np.ndarray, embeddings: np.ndarray) -> np.ndarray:
    if embeddings.size == 0 or query.size == 0:
        return np.asarray([], dtype=np.float32)

    query_norm = np.linalg.norm(query)
    embedding_norms = np.linalg.norm(embeddings, axis=1)
    denominator = np.maximum(embedding_norms * query_norm, 1e-9)
    return np.dot(embeddings, query) / denominator
