"""
AI Evaluation Factory — Main Benchmark Orchestrator
Runs V1 and V2 agents, computes delta, and auto-gates release.

Usage:
  python data/ingest.py          # build vector store (once)
  python data/synthetic_gen.py   # generate golden dataset (once)
  python main.py                 # run benchmark
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from agent.main_agent import MainAgent, warm_up
from engine.llm_judge import LLMJudge
from engine.runner import BenchmarkRunner

GOLDEN_SET = ROOT / "data" / "golden_set.jsonl"
REPORTS    = ROOT / "reports"

# ── Release gate thresholds ───────────────────────────────────────────────────
MIN_AVG_SCORE    = 3.0   # minimum acceptable avg judge score
MIN_HIT_RATE     = 0.6   # minimum retrieval hit rate
MIN_AGREEMENT    = 0.6   # minimum multi-judge agreement rate
REGRESSION_DELTA = -0.2  # V2 must not drop more than this vs V1


def load_dataset() -> list[dict]:
    if not GOLDEN_SET.exists():
        print("❌ Missing data/golden_set.jsonl — run 'python data/synthetic_gen.py' first.")
        sys.exit(1)
    with open(GOLDEN_SET, encoding="utf-8") as f:
        data = [json.loads(line) for line in f if line.strip()]
    if not data:
        print("❌ data/golden_set.jsonl is empty.")
        sys.exit(1)
    print(f"✅ Loaded {len(data)} test cases")
    return data


def build_summary(version: str, results: list[dict]) -> dict:
    n         = len(results)
    passed    = sum(1 for r in results if r["status"] == "pass")
    conflicts = sum(1 for r in results if r["judge"].get("conflict", False))

    avg_score      = sum(r["judge"]["final_score"]              for r in results) / n
    avg_hit_rate   = sum(r["ragas"]["retrieval"]["hit_rate"]    for r in results) / n
    avg_mrr        = sum(r["ragas"]["retrieval"]["mrr"]         for r in results) / n
    avg_agreement  = sum(r["judge"]["agreement_rate"]           for r in results) / n
    avg_latency    = sum(r["latency"]                           for r in results) / n
    total_tokens   = sum(r.get("tokens_used", 0)               for r in results)
    # rough cost estimate: Groq ~$0.59/1M + NVIDIA varies; use $1.00/1M as conservative avg
    est_cost_usd   = total_tokens * 0.000001

    return {
        "metadata": {
            "version":   version,
            "total":     n,
            "passed":    passed,
            "failed":    n - passed,
            "conflicts": conflicts,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "metrics": {
            "avg_score":      round(avg_score,     3),
            "hit_rate":       round(avg_hit_rate,  3),
            "avg_mrr":        round(avg_mrr,       3),
            "agreement_rate": round(avg_agreement, 3),
            "avg_latency_s":  round(avg_latency,   3),
            "total_tokens":   total_tokens,
            "est_cost_usd":   round(est_cost_usd,  4),
        },
    }


def release_gate(v1_summary: dict, v2_summary: dict) -> tuple[str, list[str]]:
    """
    Auto-decide APPROVE or BLOCK based on V2 quality vs thresholds and V1 delta.
    Returns (decision, reasons).
    """
    m2    = v2_summary["metrics"]
    delta = m2["avg_score"] - v1_summary["metrics"]["avg_score"]
    reasons: list[str] = []

    if m2["avg_score"] < MIN_AVG_SCORE:
        reasons.append(f"avg_score {m2['avg_score']:.2f} < threshold {MIN_AVG_SCORE}")
    if m2["hit_rate"] < MIN_HIT_RATE:
        reasons.append(f"hit_rate {m2['hit_rate']:.2f} < threshold {MIN_HIT_RATE}")
    if m2["agreement_rate"] < MIN_AGREEMENT:
        reasons.append(f"agreement_rate {m2['agreement_rate']:.2f} < threshold {MIN_AGREEMENT}")
    if delta < REGRESSION_DELTA:
        reasons.append(f"regression delta {delta:+.2f} below floor {REGRESSION_DELTA}")

    return ("APPROVE" if not reasons else "BLOCK"), reasons


async def run_benchmark(version: str, dataset: list[dict], judge: LLMJudge) -> tuple[list[dict], dict]:
    print(f"\n{'='*55}")
    print(f"  Running benchmark: {version}")
    print(f"{'='*55}")
    agent   = MainAgent(version=version)
    runner  = BenchmarkRunner(agent=agent, judge=judge)
    t0      = time.perf_counter()
    results = await runner.run_all(dataset, batch_size=20)
    elapsed = time.perf_counter() - t0
    print(f"  ✅ Done in {elapsed:.1f}s")
    summary = build_summary(version, results)
    return results, summary


async def main():
    print("🔧 Warming up embedding model and ChromaDB …")
    warm_up()

    dataset = load_dataset()
    dataset = dataset[:50]  # limit to 30 cases for quick benchmarking; adjust as needed

    shared_judge = LLMJudge()  # one instance, two NVIDIA clients reused across V1+V2

    print("\nRunning V1 and V2 benchmarks concurrently …")
    (v1_results, v1_summary), (v2_results, v2_summary) = await asyncio.gather(
        run_benchmark("v1", dataset, shared_judge),
        run_benchmark("v2", dataset, shared_judge),
    )

    # ── Print comparison ──────────────────────────────────────────────────────
    m1, m2   = v1_summary["metrics"], v2_summary["metrics"]
    md1, md2 = v1_summary["metadata"], v2_summary["metadata"]
    W = 68

    def bar(value: float, max_val: float = 5.0, width: int = 20) -> str:
        filled = int(round(value / max_val * width))
        return "█" * filled + "░" * (width - filled)

    def delta_arrow(d: float) -> str:
        if d > 0.01:  return f"▲ +{d:.3f}"
        if d < -0.01: return f"▼  {d:.3f}"
        return        f"  ={d:.3f}"

    print("\n" + "═" * W)
    print(f"  {'AI EVALUATION BENCHMARK — FULL REPORT':^{W-4}}")
    print(f"  {'Timestamp: ' + md2['timestamp']:^{W-4}}")
    print("═" * W)

    # ── Per-version summary boxes ─────────────────────────────────────────────
    print(f"\n  {'── V1  (Baseline) ──':^{W-4}}")
    print(f"  {'─'*32}")
    print(f"  Cases   : {md1['total']:>4}  |  Passed : {md1['passed']:>4}  |  Failed : {md1['failed']:>4}  |  Conflicts : {md1['conflicts']:>3}")
    pass_pct1 = md1['passed'] / md1['total'] * 100 if md1['total'] else 0
    print(f"  Pass rate: {pass_pct1:5.1f}%  [{bar(pass_pct1, 100)}]")
    print(f"  Avg Judge Score : {m1['avg_score']:.3f} / 5.0  [{bar(m1['avg_score'])}]")
    print(f"  Hit Rate        : {m1['hit_rate']:.3f}        [{bar(m1['hit_rate'], 1.0)}]")
    print(f"  MRR             : {m1['avg_mrr']:.3f}        [{bar(m1['avg_mrr'], 1.0)}]")
    print(f"  Agreement Rate  : {m1['agreement_rate']:.3f}        [{bar(m1['agreement_rate'], 1.0)}]")
    print(f"  Avg Latency     : {m1['avg_latency_s']:.3f} s")
    print(f"  Tokens Used     : {m1['total_tokens']:,}")
    print(f"  Est. Cost       : ${m1['est_cost_usd']:.4f} USD")

    print(f"\n  {'── V2  (Optimized) ──':^{W-4}}")
    print(f"  {'─'*32}")
    print(f"  Cases   : {md2['total']:>4}  |  Passed : {md2['passed']:>4}  |  Failed : {md2['failed']:>4}  |  Conflicts : {md2['conflicts']:>3}")
    pass_pct2 = md2['passed'] / md2['total'] * 100 if md2['total'] else 0
    print(f"  Pass rate: {pass_pct2:5.1f}%  [{bar(pass_pct2, 100)}]")
    print(f"  Avg Judge Score : {m2['avg_score']:.3f} / 5.0  [{bar(m2['avg_score'])}]")
    print(f"  Hit Rate        : {m2['hit_rate']:.3f}        [{bar(m2['hit_rate'], 1.0)}]")
    print(f"  MRR             : {m2['avg_mrr']:.3f}        [{bar(m2['avg_mrr'], 1.0)}]")
    print(f"  Agreement Rate  : {m2['agreement_rate']:.3f}        [{bar(m2['agreement_rate'], 1.0)}]")
    print(f"  Avg Latency     : {m2['avg_latency_s']:.3f} s")
    print(f"  Tokens Used     : {m2['total_tokens']:,}")
    print(f"  Est. Cost       : ${m2['est_cost_usd']:.4f} USD")

    # ── Regression delta table ────────────────────────────────────────────────
    METRIC_LABELS = {
        "avg_score":      ("Avg Judge Score (/5)", True),
        "hit_rate":       ("Hit Rate",             True),
        "avg_mrr":        ("MRR",                  True),
        "agreement_rate": ("Agreement Rate",        True),
        "avg_latency_s":  ("Avg Latency (s)",       False),  # lower is better
    }
    print(f"\n  {'─'*60}")
    print(f"  {'📊  REGRESSION COMPARISON  (V2 vs V1)':^56}")
    print(f"  {'─'*60}")
    print(f"  {'Metric':<24} {'V1':>7} {'V2':>7} {'Delta':>12}  {'Status'}")
    print(f"  {'─'*60}")
    for key, (label, higher_better) in METRIC_LABELS.items():
        d = m2[key] - m1[key]
        arrow = delta_arrow(d)
        improved = d > 0 if higher_better else d < 0
        status = "✓" if improved else ("–" if abs(d) <= 0.01 else "✗")
        print(f"  {label:<24} {m1[key]:>7.3f} {m2[key]:>7.3f} {arrow:>12}  {status}")
    print(f"  {'─'*60}")

    cost_delta = m2['est_cost_usd'] - m1['est_cost_usd']
    tok_delta  = m2['total_tokens'] - m1['total_tokens']
    print(f"  {'Total Tokens':<24} {m1['total_tokens']:>7,} {m2['total_tokens']:>7,}  Δ {tok_delta:>+,}")
    print(f"  {'Est. Cost (USD)':<24} ${m1['est_cost_usd']:>6.4f} ${m2['est_cost_usd']:>6.4f}  Δ ${cost_delta:>+.4f}")

    # ── Release gate ─────────────────────────────────────────────────────────
    decision, reasons = release_gate(v1_summary, v2_summary)
    gate_icon = "✅" if decision == "APPROVE" else "🚫"
    print(f"\n{'═' * W}")
    print(f"  🚦  RELEASE GATE: {gate_icon}  {decision}")
    print(f"{'─' * W}")
    if reasons:
        for r in reasons:
            print(f"     ✗  {r}")
    else:
        print("     ✓  All quality / regression thresholds passed")
    print(f"  Thresholds: avg_score ≥ {MIN_AVG_SCORE}  |  hit_rate ≥ {MIN_HIT_RATE}"
          f"  |  agreement ≥ {MIN_AGREEMENT}  |  regression ≥ {REGRESSION_DELTA}")
    print("═" * W)

    # ── Save reports ─────────────────────────────────────────────────────────
    REPORTS.mkdir(exist_ok=True)

    v2_summary["regression"] = {
        "v1_avg_score": m1["avg_score"],
        "delta":        round(m2["avg_score"] - m1["avg_score"], 3),
        "decision":     decision,
        "reasons":      reasons,
    }

    (REPORTS / "summary.json").write_text(
        json.dumps(v2_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (REPORTS / "benchmark_results.json").write_text(
        json.dumps({"v1": v1_results, "v2": v2_results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n✅ Reports saved to reports/")


if __name__ == "__main__":
    asyncio.run(main())
