"""
Async Benchmark Runner — processes test cases in batches to avoid rate limits.
"""
import asyncio
import time
from typing import Dict, List

from engine.llm_judge import LLMJudge
from engine.retrieval_eval import RetrievalEvaluator


class BenchmarkRunner:
    def __init__(self, agent, judge: LLMJudge | None = None):
        self.agent     = agent
        self.judge     = judge or LLMJudge()
        self.evaluator = RetrievalEvaluator()

    async def run_single_test(self, test_case: Dict) -> Dict:
        start = time.perf_counter()

        # 1. RAG agent
        response = await self.agent.query(test_case["question"])
        latency  = time.perf_counter() - start

        # 2. Retrieval metrics
        expected_ids = test_case.get("expected_retrieval_ids", [])
        retrieved    = response.get("retrieved_ids", [])
        hit_rate     = self.evaluator.calculate_hit_rate(expected_ids, retrieved)
        mrr          = self.evaluator.calculate_mrr(expected_ids, retrieved)

        # 3. Multi-judge scoring
        judge_result = await self.judge.evaluate_multi_judge(
            question=test_case["question"],
            answer=response["answer"],
            ground_truth=test_case.get("expected_answer", ""),
        )

        return {
            "question":       test_case["question"],
            "agent_answer":   response["answer"],
            "expected_answer": test_case.get("expected_answer", ""),
            "latency":        round(latency, 3),
            "tokens_used":    response.get("metadata", {}).get("tokens_used", 0),
            "ragas": {
                "retrieval": {
                    "hit_rate": hit_rate,
                    "mrr":      mrr,
                },
            },
            "judge":          judge_result,
            "status":         "pass" if judge_result["final_score"] >= 3 else "fail",
            "metadata":       test_case.get("metadata", {}),
        }

    async def run_all(
        self, dataset: List[Dict], batch_size: int = 5
    ) -> List[Dict]:
        """Process dataset in batches to stay within API rate limits."""
        results = []
        total   = len(dataset)

        for i in range(0, total, batch_size):
            batch        = dataset[i : i + batch_size]
            batch_num    = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size
            print(f"  Batch {batch_num}/{total_batches} ({len(batch)} cases) …")

            tasks         = [self.run_single_test(case) for case in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

        return results
