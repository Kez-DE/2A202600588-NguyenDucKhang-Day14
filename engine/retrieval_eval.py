from typing import Dict, List


class RetrievalEvaluator:
    def calculate_hit_rate(self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3) -> float:
        if not expected_ids:
            return 1.0 if not retrieved_ids else 0.0
        top_retrieved = retrieved_ids[:top_k]
        return 1.0 if any(doc_id in top_retrieved for doc_id in expected_ids) else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        if not expected_ids:
            return 1.0 if not retrieved_ids else 0.0
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    async def score(self, case: Dict, response: Dict) -> Dict:
        expected_ids = case.get("expected_retrieval_ids", [])
        retrieved_ids = response.get("retrieved_ids", [])
        hit_rate = self.calculate_hit_rate(expected_ids, retrieved_ids)
        mrr = self.calculate_mrr(expected_ids, retrieved_ids)

        answer = response.get("answer", "").lower()
        contexts = " ".join(response.get("contexts", [])).lower()
        context_tokens = {token for token in contexts.split() if len(token) > 3}
        answer_tokens = {token for token in answer.split() if len(token) > 3}
        grounded_overlap = len(answer_tokens & context_tokens) / max(len(answer_tokens), 1)

        return {
            "faithfulness": round(min(1.0, grounded_overlap + 0.2), 3) if contexts else (1.0 if "không tìm thấy" in answer else 0.0),
            "relevancy": round((hit_rate + mrr) / 2, 3),
            "retrieval": {
                "hit_rate": hit_rate,
                "mrr": mrr,
                "expected_ids": expected_ids,
                "retrieved_ids": retrieved_ids,
            },
        }

    async def evaluate_batch(self, dataset: List[Dict], responses: List[Dict]) -> Dict:
        scores = [await self.score(case, response) for case, response in zip(dataset, responses)]
        total = len(scores) or 1
        return {
            "avg_hit_rate": sum(item["retrieval"]["hit_rate"] for item in scores) / total,
            "avg_mrr": sum(item["retrieval"]["mrr"] for item in scores) / total,
        }
