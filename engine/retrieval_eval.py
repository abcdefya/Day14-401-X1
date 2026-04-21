"""
Retrieval Evaluator — computes Hit Rate and MRR for each test case.
Requires the agent to return 'retrieved_ids' in its response.
"""
from typing import Dict, List


class RetrievalEvaluator:
    def calculate_hit_rate(
        self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3
    ) -> float:
        """1.0 if any expected_id appears in the top_k retrieved results, else 0.0."""
        if not expected_ids:
            return 1.0  # adversarial / out-of-context: no retrieval expected
        top = retrieved_ids[:top_k]
        return 1.0 if any(eid in top for eid in expected_ids) else 0.0

    def calculate_mrr(
        self, expected_ids: List[str], retrieved_ids: List[str]
    ) -> float:
        """Mean Reciprocal Rank: 1/position of first relevant result (1-indexed)."""
        if not expected_ids:
            return 1.0  # adversarial / out-of-context: no retrieval expected
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    async def evaluate_batch(self, dataset: List[Dict], agent) -> Dict:
        """
        Run retrieval eval for the whole dataset.
        Each case must have 'expected_retrieval_ids'.
        Agent response must have 'retrieved_ids'.

        Returns aggregated hit_rate and mrr, plus per-case details.
        """
        hit_rates: List[float] = []
        mrrs:      List[float] = []
        details:   List[Dict]  = []

        for case in dataset:
            response  = await agent.query(case["question"])
            retrieved = response.get("retrieved_ids", [])
            expected  = case.get("expected_retrieval_ids", [])

            hr  = self.calculate_hit_rate(expected, retrieved)
            mrr = self.calculate_mrr(expected, retrieved)
            hit_rates.append(hr)
            mrrs.append(mrr)

            details.append({
                "question":    case["question"],
                "expected":    expected,
                "retrieved":   retrieved,
                "hit_rate":    hr,
                "mrr":         mrr,
            })

        n = len(hit_rates)
        return {
            "avg_hit_rate": sum(hit_rates) / n if n else 0.0,
            "avg_mrr":      sum(mrrs)      / n if n else 0.0,
            "details":      details,
        }
