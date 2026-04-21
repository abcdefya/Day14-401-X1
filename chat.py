"""
Streamlit Chat UI — XanhSM Support Agent
Ask a question → get answers from V1 & V2 agents + LLM judge metrics side by side.

Run:
  streamlit run chat.py
"""
import asyncio
import sys
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="XanhSM Support Agent",
    page_icon="🟢",
    layout="wide",
)

# ── Warm-up (cached so it runs only once per session) ─────────────────────────
@st.cache_resource(show_spinner="Loading embedding model & ChromaDB …")
def load_resources():
    from agent.main_agent import MainAgent, warm_up
    from engine.llm_judge import LLMJudge

    warm_up()
    return {
        "v1":    MainAgent(version="v1"),
        "v2":    MainAgent(version="v2"),
        "judge": LLMJudge(),
    }


resources = load_resources()


# ── Helpers ───────────────────────────────────────────────────────────────────
def bar(value: float, max_val: float = 5.0, width: int = 16) -> str:
    filled = int(round(value / max_val * width))
    return "█" * filled + "░" * (width - filled)


def score_color(score: float) -> str:
    if score >= 4:   return "green"
    if score >= 3:   return "orange"
    return "red"


async def ask_both(question: str) -> dict:
    """Run V1, V2 agents and judge concurrently."""
    from engine.retrieval_eval import RetrievalEvaluator

    evaluator = RetrievalEvaluator()
    v1_agent  = resources["v1"]
    v2_agent  = resources["v2"]
    judge     = resources["judge"]

    t0 = time.perf_counter()

    async def run_agent(agent):
        t = time.perf_counter()
        resp = await agent.query(question)
        return resp, round(time.perf_counter() - t, 3)

    (v1_resp, v1_lat), (v2_resp, v2_lat) = await asyncio.gather(
        run_agent(v1_agent),
        run_agent(v2_agent),
    )

    # Judge both answers (no ground truth in live chat → pass empty string)
    (v1_judge, v2_judge) = await asyncio.gather(
        judge.evaluate_multi_judge(question, v1_resp["answer"], ""),
        judge.evaluate_multi_judge(question, v2_resp["answer"], ""),
    )

    return {
        "question": question,
        "v1": {
            "answer":        v1_resp["answer"],
            "retrieved_ids": v1_resp["retrieved_ids"],
            "contexts":      v1_resp["contexts"],
            "latency":       v1_lat,
            "tokens":        v1_resp["metadata"].get("tokens_used", 0),
            "judge":         v1_judge,
        },
        "v2": {
            "answer":        v2_resp["answer"],
            "retrieved_ids": v2_resp["retrieved_ids"],
            "contexts":      v2_resp["contexts"],
            "latency":       v2_lat,
            "tokens":        v2_resp["metadata"].get("tokens_used", 0),
            "judge":         v2_judge,
        },
        "total_latency": round(time.perf_counter() - t0, 3),
    }


def render_judge_metrics(judge: dict, version: str):
    score = judge["final_score"]
    color = score_color(score)

    st.markdown(f"**Judge Score:** :{color}[{score:.1f} / 5.0]")
    st.text(f"{bar(score)}  {score:.1f}")

    cols = st.columns(2)
    with cols[0]:
        agree = judge["agreement_rate"]
        st.metric("Agreement", f"{agree:.0%}", help="1.0 = judges agree, 0.0 = conflict")
    with cols[1]:
        conflict_val = "Yes ⚠️" if judge["conflict"] else "No ✓"
        st.metric("Conflict", conflict_val)

    with st.expander("Individual judge scores"):
        for model, s in judge["individual_scores"].items():
            short = model.split("/")[-1]
            st.markdown(f"- **{short}**: `{s}` — {judge['reasoning'].get(model, '')}")


def render_result_card(data: dict, version: str):
    v = data[version]
    judge = v["judge"]
    score = judge["final_score"]
    color = score_color(score)

    label = "Baseline (V1)" if version == "v1" else "Optimized (V2)"
    st.subheader(f"{'🔵' if version == 'v1' else '🟢'}  {label}")

    # Answer box
    st.markdown("**Answer**")
    st.info(v["answer"])

    # Quick stats row
    c1, c2, c3 = st.columns(3)
    c1.metric("Judge Score", f"{score:.2f} / 5", delta=None)
    c2.metric("Latency", f"{v['latency']} s")
    c3.metric("Tokens", f"{v['tokens']:,}")

    # Judge details
    st.markdown("**LLM Judge Metrics**")
    render_judge_metrics(judge, version)

    # Retrieved chunks
    with st.expander(f"Retrieved context chunks ({len(v['retrieved_ids'])})"):
        for i, (doc_id, ctx) in enumerate(zip(v["retrieved_ids"], v["contexts"]), 1):
            st.markdown(f"**[{i}] `{doc_id}`**")
            st.caption(ctx[:400] + ("…" if len(ctx) > 400 else ""))


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🟢 XanhSM Support")
    st.markdown("Ask anything about XanhSM services.")
    st.divider()
    st.markdown("**Models**")
    st.markdown("- Agent: `nvidia/llama-3.1-nemotron-nano-8b-v1`")
    st.markdown("- Judge 1: `nvidia/llama-3.1-nemotron-nano-8b-v1`")
    st.markdown("- Judge 2: `nvidia/llama-3.3-nemotron-super-49b-v1`")
    st.divider()
    if st.button("Clear chat history"):
        st.session_state.history = []
        st.rerun()
    st.markdown("---")
    st.caption("Run `python data/ingest.py` first to build the vector store.")


# ── Main layout ───────────────────────────────────────────────────────────────
st.title("🟢 XanhSM AI Support — V1 vs V2")
st.caption("Each question is answered by both agents and scored by dual LLM judges in real time.")

# Session state
if "history" not in st.session_state:
    st.session_state.history = []

# Render past conversations
for entry in st.session_state.history:
    with st.chat_message("user"):
        st.markdown(entry["question"])
    with st.chat_message("assistant"):
        col1, col2 = st.columns(2)
        with col1:
            render_result_card(entry, "v1")
        with col2:
            render_result_card(entry, "v2")

        # Delta summary
        s1 = entry["v1"]["judge"]["final_score"]
        s2 = entry["v2"]["judge"]["final_score"]
        d  = s2 - s1
        sign = f"+{d:.2f}" if d >= 0 else f"{d:.2f}"
        color = "green" if d >= 0 else "red"
        st.caption(
            f"V2 vs V1 score delta: :{color}[**{sign}**]  |  "
            f"Total latency: {entry['total_latency']} s"
        )

# Chat input
if question := st.chat_input("Hỏi về dịch vụ XanhSM …"):
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Querying agents and judges …"):
            result = asyncio.run(ask_both(question))

        col1, col2 = st.columns(2)
        with col1:
            render_result_card(result, "v1")
        with col2:
            render_result_card(result, "v2")

        s1 = result["v1"]["judge"]["final_score"]
        s2 = result["v2"]["judge"]["final_score"]
        d  = s2 - s1
        sign = f"+{d:.2f}" if d >= 0 else f"{d:.2f}"
        color = "green" if d >= 0 else "red"
        st.caption(
            f"V2 vs V1 score delta: :{color}[**{sign}**]  |  "
            f"Total latency: {result['total_latency']} s"
        )

    st.session_state.history.append(result)
