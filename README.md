# XanhSM AI Evaluation Factory

Automated benchmarking system to evaluate a RAG-based AI support agent for XanhSM (Vietnamese ride-hailing / food-delivery platform). Measures retrieval quality, answer accuracy via multi-judge consensus, and gates releases through regression testing.

---

## Project Structure

```
Day14-401-X1/
│
├── agent/
│   ├── __init__.py
│   └── main_agent.py          # RAG agent (ChromaDB retrieval + Groq LLM)
│                              #   V1: basic prompt
│                              #   V2: grounded system prompt (anti-hallucination)
│
├── data/
│   ├── GSM/                   # Source FAQ documents (Markdown)
│   │   ├── XanhSM - User FAQs.md
│   │   ├── XanhSM - electric_car_driver FAQs.md
│   │   ├── XanhSM - electric_motor_driver FAQs.md
│   │   └── XanhSM - Restaurant FAQs.md
│   ├── ingest.py              # Chunking + embedding pipeline → ChromaDB
│   ├── synthetic_gen.py       # SDG: generates golden_set.jsonl via Groq
│   ├── golden_set.jsonl       # 50+ test cases (generated, not committed)
│   └── HARD_CASES_GUIDE.md    # Guide for designing adversarial test cases
│
├── engine/
│   ├── __init__.py
│   ├── llm_judge.py           # Multi-judge: Groq llama-3.3-70b + gpt-oss-120b
│   ├── retrieval_eval.py      # Hit Rate & MRR computation
│   └── runner.py              # Async batch benchmark runner
│
├── analysis/
│   └── failure_analysis.md    # 5-Whys root cause analysis + action plan
│
├── reports/                   # Generated after running main.py (not committed)
│   ├── summary.json
│   └── benchmark_results.json
│
├── main.py                    # Orchestrator: V1 vs V2 benchmark + release gate
├── check_lab.py               # Pre-submission validator
├── requirements.txt
├── .env.example               # Environment variable template
└── GRADING_RUBRIC.md
```

---

## Architecture

```
FAQ Markdown files
       │
       ▼
  data/ingest.py
  (chunk by ## header, embed with HuggingFace, store in ChromaDB)
       │
       ▼
  ChromaDB (./chroma_db)
       │
  ┌────┴────────────────────────┐
  │                             │
  ▼                             ▼
agent/main_agent.py       data/synthetic_gen.py
(RAG: retrieve + Groq)    (generate golden_set.jsonl via Groq)
  │
  ▼
engine/runner.py  ──── engine/llm_judge.py   (Judge 1: llama-3.3-70b)
  │               └─── engine/llm_judge.py   (Judge 2: gpt-oss-120b)
  │               └─── engine/retrieval_eval.py  (Hit Rate, MRR)
  │
  ▼
main.py
(V1 vs V2 regression → release gate → reports/)
```

---

## Setup

**1. Clone & create virtual environment**
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Configure environment**
```bash
cp .env.example .env
```

Edit `.env` and fill in your API keys:
```
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_MODEL_2=openai/gpt-oss-120b
HF_MODEL=paraphrase-multilingual-MiniLM-L12-v2
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=GSM_Collection
DATA_DIR=./data
```

Get a free Groq API key at: https://console.groq.com

---

## Run

```bash
# Step 1 — Build vector store (run once)
python data/ingest.py

# Step 2 — Generate golden dataset (run once)
python data/synthetic_gen.py

# Step 3 — Run full benchmark
python main.py

# Step 4 — Validate before submission
python check_lab.py
```

Steps 1 and 2 only need to run once. Re-run `main.py` as many times as needed.

---

## What main.py does

1. Loads `data/golden_set.jsonl` (50+ test cases)
2. Runs **Agent V1** (basic prompt) across all cases
3. Runs **Agent V2** (grounded prompt) across all cases
4. For each case computes:
   - **Hit Rate** (top-3) and **MRR** — retrieval quality
   - **Multi-judge score** — both Groq judges score 1–5, averaged
   - **Agreement rate** — flags conflicts when `|score_1 - score_2| > 1`
   - **Latency** and **token cost**
5. Prints V1 vs V2 regression table
6. Auto-decides **APPROVE** or **BLOCK** based on thresholds:
   - `avg_score >= 3.0`
   - `hit_rate >= 0.6`
   - `agreement_rate >= 0.6`
   - V2 regression delta `>= -0.2`
7. Saves `reports/summary.json` and `reports/benchmark_results.json`

---

## Key Metrics

| Metric | Description |
|--------|-------------|
| Hit Rate @3 | Fraction of cases where the correct chunk appears in top-3 retrieved results |
| MRR | Mean Reciprocal Rank of the first relevant retrieved chunk |
| Judge Score | Average of 2 LLM judges on 1–5 scale |
| Agreement Rate | Fraction of cases where both judges agree (diff ≤ 1) |
| Est. Cost (USD) | Token usage × per-token price for the benchmark run |

---

## Test Case Types

The golden dataset includes:
- **Fact-check** — single-source factual questions
- **Multi-fact** — questions requiring multiple details from one chunk
- **Multi-hop** — questions spanning multiple FAQ sections
- **Out-of-context** — questions not covered in any document (agent must say "I don't know")
- **Prompt injection / Goal hijacking** — adversarial inputs to test guardrails
- **Time-sensitive** — questions about policies with specific dates

---

## Notes

- `.env` is gitignored — never commit API keys
- `data/golden_set.jsonl` and `chroma_db/` are gitignored — regenerate locally
- `reports/` output is committed for grading purposes
