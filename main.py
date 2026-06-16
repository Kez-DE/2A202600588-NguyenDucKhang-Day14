import asyncio
import json
import os
import time
from typing import Dict, List, Tuple

from agent.main_agent import MainAgent
from data.synthetic_gen import main as generate_dataset
from engine.llm_judge import LLMJudge
from engine.retrieval_eval import RetrievalEvaluator
from engine.runner import BenchmarkRunner


QUALITY_THRESHOLDS = {
    "min_avg_score": 3.5,
    "min_hit_rate": 0.86,
    "min_mrr": 0.78,
    "min_agreement_rate": 0.55,
    "max_latency_p95": 0.15,
    "max_cost_usd": 0.05,
}


def load_dataset() -> List[Dict]:
    if not os.path.exists("data/golden_set.jsonl") or not os.path.exists("data/knowledge_base.json"):
        print("data/golden_set.jsonl hoặc data/knowledge_base.json chưa có. Đang tạo dataset offline...")
        asyncio.run(generate_dataset())

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if len(dataset) < 50:
        raise ValueError(f"Golden dataset cần ít nhất 50 cases, hiện có {len(dataset)}.")
    return dataset


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((pct / 100) * (len(ordered) - 1))))
    return ordered[index]


def summarize(version: str, results: List[Dict], elapsed: float) -> Dict:
    total = len(results)
    pass_count = sum(1 for result in results if result["status"] == "pass")
    total_tokens = sum(result["tokens_used"] for result in results)
    estimated_cost = total_tokens / 1000 * 0.00015

    metrics = {
        "avg_score": round(sum(r["judge"]["final_score"] for r in results) / total, 3),
        "hit_rate": round(sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total, 3),
        "mrr": round(sum(r["ragas"]["retrieval"]["mrr"] for r in results) / total, 3),
        "faithfulness": round(sum(r["ragas"]["faithfulness"] for r in results) / total, 3),
        "relevancy": round(sum(r["ragas"]["relevancy"] for r in results) / total, 3),
        "agreement_rate": round(sum(r["judge"]["agreement_rate"] for r in results) / total, 3),
        "cohen_kappa": round(sum(r["judge"]["cohen_kappa"] for r in results) / total, 3),
        "conflict_rate": round(sum(1 for r in results if r["judge"]["conflict"]) / total, 3),
        "pass_rate": round(pass_count / total, 3),
        "latency_avg": round(sum(r["latency"] for r in results) / total, 4),
        "latency_p95": round(percentile([r["latency"] for r in results], 95), 4),
        "tokens_total": total_tokens,
        "estimated_cost_usd": round(estimated_cost, 6),
    }

    return {
        "metadata": {
            "version": version,
            "total": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_seconds": round(elapsed, 3),
            "async_batch_size": 10,
            "judge_models": ["gpt-4o-rubric-sim", "claude-3-5-rubric-sim"],
        },
        "metrics": metrics,
    }


async def run_benchmark_with_results(agent_version: str, dataset: List[Dict]) -> Tuple[List[Dict], Dict]:
    print(f"Benchmark {agent_version}: {len(dataset)} cases")
    start = time.perf_counter()
    runner = BenchmarkRunner(MainAgent(version="v2" if "V2" in agent_version else "v1"), RetrievalEvaluator(), LLMJudge())
    results = await runner.run_all(dataset, batch_size=10)
    elapsed = time.perf_counter() - start
    return results, summarize(agent_version, results, elapsed)


def release_gate(v1_summary: Dict, v2_summary: Dict) -> Dict:
    v1 = v1_summary["metrics"]
    v2 = v2_summary["metrics"]
    deltas = {
        "avg_score": round(v2["avg_score"] - v1["avg_score"], 3),
        "hit_rate": round(v2["hit_rate"] - v1["hit_rate"], 3),
        "mrr": round(v2["mrr"] - v1["mrr"], 3),
        "estimated_cost_usd": round(v2["estimated_cost_usd"] - v1["estimated_cost_usd"], 6),
    }

    checks = {
        "avg_score": v2["avg_score"] >= QUALITY_THRESHOLDS["min_avg_score"],
        "hit_rate": v2["hit_rate"] >= QUALITY_THRESHOLDS["min_hit_rate"],
        "mrr": v2["mrr"] >= QUALITY_THRESHOLDS["min_mrr"],
        "agreement_rate": v2["agreement_rate"] >= QUALITY_THRESHOLDS["min_agreement_rate"],
        "latency_p95": v2["latency_p95"] <= QUALITY_THRESHOLDS["max_latency_p95"],
        "cost": v2["estimated_cost_usd"] <= QUALITY_THRESHOLDS["max_cost_usd"],
        "no_quality_regression": deltas["avg_score"] >= -0.05 and deltas["hit_rate"] >= -0.02,
    }
    decision = "APPROVE" if all(checks.values()) else "BLOCK_RELEASE"
    return {"decision": decision, "checks": checks, "thresholds": QUALITY_THRESHOLDS, "deltas": deltas}


async def main():
    dataset = load_dataset()
    v1_results, v1_summary = await run_benchmark_with_results("Agent_V1_Base", dataset)
    v2_results, v2_summary = await run_benchmark_with_results("Agent_V2_Optimized", dataset)
    gate = release_gate(v1_summary, v2_summary)

    summary = {
        **v2_summary,
        "regression": {
            "baseline": v1_summary,
            "candidate": v2_summary,
            "release_gate": gate,
        },
    }

    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump({"v1": v1_results, "v2": v2_results}, f, ensure_ascii=False, indent=2)

    print("\n--- Regression Summary ---")
    print(f"V1 avg_score={v1_summary['metrics']['avg_score']} hit_rate={v1_summary['metrics']['hit_rate']} mrr={v1_summary['metrics']['mrr']}")
    print(f"V2 avg_score={v2_summary['metrics']['avg_score']} hit_rate={v2_summary['metrics']['hit_rate']} mrr={v2_summary['metrics']['mrr']}")
    print(f"Decision: {gate['decision']}")
    print("Saved reports/summary.json and reports/benchmark_results.json")


if __name__ == "__main__":
    asyncio.run(main())
