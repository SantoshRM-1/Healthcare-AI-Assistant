"""Small transparent retrieval metric helpers for labeled offline evaluation."""
from __future__ import annotations

from collections.abc import Iterable


def score_retrieval(ranked_ids: Iterable[str], relevant_ids: set[str], *, k: int = 5) -> dict[str, float]:
    """Calculate precision@k, recall@k, and reciprocal rank for one labeled query."""
    if k <= 0:
        raise ValueError("k must be positive")
    ranked = list(ranked_ids)[:k]
    hits = sum(identifier in relevant_ids for identifier in ranked)
    reciprocal_rank = next(
        (1.0 / rank for rank, identifier in enumerate(ranked, start=1) if identifier in relevant_ids),
        0.0,
    )
    return {
        f"precision@{k}": hits / k,
        f"recall@{k}": hits / len(relevant_ids) if relevant_ids else 0.0,
        "mrr": reciprocal_rank,
    }


def mean_retrieval_scores(scores: Iterable[dict[str, float]]) -> dict[str, float]:
    """Macro average labeled-query scores; empty datasets report zero metrics."""
    materialized = list(scores)
    if not materialized:
        return {"precision": 0.0, "recall": 0.0, "mrr": 0.0}
    keys = list(materialized[0])
    return {key: sum(item[key] for item in materialized) / len(materialized) for key in keys}
