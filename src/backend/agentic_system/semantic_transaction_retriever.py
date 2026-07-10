"""Pure embedding-based semantic retrieval for customer transactions."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, ClassVar
import numpy as np

try:
    from .agent_support import RetrievalQueryTranslator
except ImportError:  # Allows direct script-style imports during prototyping.
    from agent_support import RetrievalQueryTranslator


DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_SIMILARITY_THRESHOLD = 0.34


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
        self.documents = [
            _transaction_document(transaction) for transaction in transactions
        ]
        self.chunks = _transaction_chunks(transactions)
        self.embeddings = self._embed_texts([chunk["text"] for chunk in self.chunks])

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
        translated_query = RetrievalQueryTranslator.translate(search_query)
        query_embedding = self._embed_texts([translated_query])[0]
        scores = _cosine_scores(query_embedding, self.embeddings)
        ranked = _rank_transactions_by_best_chunk(
            transactions=self.transactions,
            chunks=self.chunks,
            scores=scores,
            threshold=self.threshold,
        )
        ranked.sort(key=lambda result: result.score, reverse=True)
        ranked = _drop_weak_tail_after_strong_match(ranked)
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


def _transaction_chunks(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks = []
    for transaction_index, transaction in enumerate(transactions):
        chunk_values = [
            ("merchant", transaction.get("merchant")),
            ("retrieval_text", transaction.get("retrieval_text")),
            ("display_name", transaction.get("display_name")),
        ]
        added = False
        for field, value in chunk_values:
            if value is None or not str(value).strip():
                continue
            chunks.append(
                {
                    "transaction_index": transaction_index,
                    "field": field,
                    "text": str(value),
                }
            )
            added = True
        if not added:
            chunks.append(
                {
                    "transaction_index": transaction_index,
                    "field": "transaction",
                    "text": _transaction_document(transaction),
                }
            )
    return chunks


def _rank_transactions_by_best_chunk(
    *,
    transactions: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    scores: np.ndarray,
    threshold: float,
) -> list[TransactionSearchResult]:
    best_scores: dict[int, float] = {}
    for chunk, score in zip(chunks, scores):
        transaction_index = int(chunk["transaction_index"])
        numeric_score = float(score)
        if numeric_score < threshold:
            continue
        best_scores[transaction_index] = max(
            numeric_score,
            best_scores.get(transaction_index, float("-inf")),
        )
    return [
        TransactionSearchResult(
            transaction=transactions[index],
            score=score,
        )
        for index, score in best_scores.items()
    ]


def _drop_weak_tail_after_strong_match(
    ranked: list[TransactionSearchResult],
) -> list[TransactionSearchResult]:
    if not ranked:
        return ranked
    top_score = ranked[0].score
    if top_score < 0.75:
        return ranked
    relative_floor = top_score * 0.65
    return [result for result in ranked if result.score >= relative_floor]


def _cosine_scores(query: np.ndarray, embeddings: np.ndarray) -> np.ndarray:
    if embeddings.size == 0 or query.size == 0:
        return np.asarray([], dtype=np.float32)
    query_norm = np.linalg.norm(query)
    embedding_norms = np.linalg.norm(embeddings, axis=1)
    denominator = np.maximum(embedding_norms * query_norm, 1e-9)
    return np.dot(embeddings, query) / denominator
