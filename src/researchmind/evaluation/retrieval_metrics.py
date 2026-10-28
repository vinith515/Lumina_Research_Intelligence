"""Evaluation metrics for information retrieval, evidence ranking, and abstention."""

import math
from typing import List, Set, Sequence, Dict, Any, Optional


def compute_recall_at_k(retrieved_ids: Sequence[str], relevant_ids: Set[str], k: int) -> float:
    """Compute Recall@K: Proportion of relevant items retrieved in top K (deduplicated)."""
    if not relevant_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    hits = len(set(item for item in top_k if item in relevant_ids))
    return min(1.0, hits / len(relevant_ids))


def compute_precision_at_k(retrieved_ids: Sequence[str], relevant_ids: Set[str], k: int) -> float:
    """Compute Precision@K: Proportion of top K retrieved items that are relevant."""
    if k == 0:
        return 0.0
    top_k = retrieved_ids[:k]
    hits = len(set(item for item in top_k if item in relevant_ids))
    return hits / k


def compute_hit_rate_at_k(retrieved_ids: Sequence[str], relevant_ids: Set[str], k: int) -> float:
    """Compute HitRate@K (1.0 if at least one relevant document in top K, else 0.0)."""
    if not relevant_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    return 1.0 if any(item in relevant_ids for item in top_k) else 0.0


def compute_mrr(retrieved_ids: Sequence[str], relevant_ids: Set[str]) -> float:
    """Compute Mean Reciprocal Rank (MRR): 1 / rank of the first relevant document."""
    if not relevant_ids:
        return 0.0
    for rank, item in enumerate(retrieved_ids, start=1):
        if item in relevant_ids:
            return 1.0 / rank
    return 0.0


def compute_ndcg_at_k(retrieved_ids: Sequence[str], relevant_ids: Set[str], k: int) -> float:
    """Compute Normalized Discounted Cumulative Gain (nDCG@K)."""
    if not relevant_ids:
        return 0.0

    dcg = 0.0
    seen_relevant: Set[str] = set()
    top_k = retrieved_ids[:k]
    for rank, item in enumerate(top_k, start=1):
        if item in relevant_ids and item not in seen_relevant:
            dcg += 1.0 / math.log2(rank + 1)
            seen_relevant.add(item)

    # Ideal DCG (all relevant items ranked at the top)
    idcg = 0.0
    ideal_hits = min(k, len(relevant_ids))
    for rank in range(1, ideal_hits + 1):
        idcg += 1.0 / math.log2(rank + 1)

    return (dcg / idcg) if idcg > 0 else 0.0


def compute_abstention_metrics(
    query_results: List[Dict[str, Any]]
) -> Dict[str, float]:
    """Calculate research-grade abstention and selective answering metrics.
    
    Args:
        query_results: List of dicts with keys:
            - 'answerability': 'answerable', 'partial', 'unanswerable'
            - 'abstained': bool
            - 'is_correct_answer': Optional[bool]
            
    Returns:
        Dict with Abstention Accuracy, Selective Accuracy, Unsupported Answer Rate, and False Abstention Rate.
    """
    total = len(query_results)
    if total == 0:
        return {
            "abstention_accuracy": 0.0,
            "selective_accuracy": 0.0,
            "unsupported_answer_rate": 0.0,
            "false_abstention_rate": 0.0,
        }

    unanswerable = [q for q in query_results if q["answerability"] == "unanswerable"]
    answerable = [q for q in query_results if q["answerability"] in ["answerable", "partial"]]

    # 1. Correct Abstention on Unanswerable (True Positives for Abstention)
    correct_abstentions = sum(1 for q in unanswerable if q["abstained"])
    # 2. False Answers on Unanswerable (Hallucinated answers on out-of-corpus)
    unsupported_answers = sum(1 for q in unanswerable if not q["abstained"])
    # 3. False Abstentions on Answerable (Incorrectly abstaining when evidence exists)
    false_abstentions = sum(1 for q in answerable if q["abstained"])
    # 4. Answers on Answerable
    answered_correctly = sum(1 for q in answerable if not q["abstained"])

    # Overall Abstention Accuracy: (Correct Abstentions + Correct Answers Attempted) / Total
    abstention_accuracy = (correct_abstentions + answered_correctly) / total

    # Unsupported Answer Rate: Unsupported answers / Total Unanswerable
    unsupported_answer_rate = (unsupported_answers / len(unanswerable)) if unanswerable else 0.0

    # False Abstention Rate: False Abstentions / Total Answerable
    false_abstention_rate = (false_abstentions / len(answerable)) if answerable else 0.0

    # Selective Accuracy: Answered correctly / Total answers attempted
    total_attempted = answered_correctly + unsupported_answers
    selective_accuracy = (answered_correctly / total_attempted) if total_attempted > 0 else 1.0

    return {
        "abstention_accuracy": round(abstention_accuracy, 4),
        "selective_accuracy": round(selective_accuracy, 4),
        "unsupported_answer_rate": round(unsupported_answer_rate, 4),
        "false_abstention_rate": round(false_abstention_rate, 4),
    }
