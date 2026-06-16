import asyncio
import time
from typing import Dict, List


class BenchmarkRunner:
    def __init__(self, agent, evaluator, judge):
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge

    async def run_single_test(self, test_case: Dict) -> Dict:
        start_time = time.perf_counter()
        response = await self.agent.query(test_case["question"])
        latency = time.perf_counter() - start_time

        ragas_scores = await self.evaluator.score(test_case, response)
        judge_result = await self.judge.evaluate_multi_judge(
            test_case["question"],
            response["answer"],
            test_case["expected_answer"],
        )

        status = "pass"
        if judge_result["final_score"] < 3.5 or ragas_scores["retrieval"]["hit_rate"] < 1.0:
            status = "fail"

        return {
            "id": test_case.get("id"),
            "test_case": test_case["question"],
            "expected_answer": test_case["expected_answer"],
            "expected_retrieval_ids": test_case.get("expected_retrieval_ids", []),
            "metadata": test_case.get("metadata", {}),
            "agent_response": response["answer"],
            "retrieved_ids": response.get("retrieved_ids", []),
            "latency": round(latency, 4),
            "tokens_used": response.get("metadata", {}).get("tokens_used", 0),
            "ragas": ragas_scores,
            "judge": judge_result,
            "status": status,
        }

    async def run_all(self, dataset: List[Dict], batch_size: int = 10) -> List[Dict]:
        results = []
        semaphore = asyncio.Semaphore(batch_size)

        async def guarded(case: Dict) -> Dict:
            async with semaphore:
                return await self.run_single_test(case)

        tasks = [guarded(case) for case in dataset]
        for result in await asyncio.gather(*tasks):
            results.append(result)
        return results
