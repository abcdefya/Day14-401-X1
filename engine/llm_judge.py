"""
Multi-Judge Consensus Engine.
Judge 1: Groq  GROQ_MODEL   (llama-3.3-70b-versatile)
Judge 2: Groq  GROQ_MODEL_2 (openai/gpt-oss-120b)

Scoring rubric: 1-5 for accuracy vs ground truth.
Conflict resolution: if |score_A - score_B| > 1 → flag as conflict, still average.
Agreement rate = fraction of cases where |score_A - score_B| <= 1.
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

GROQ_MODEL   = os.getenv("GROQ_MODEL",   "llama-3.3-70b-versatile")
GROQ_MODEL_2 = os.getenv("GROQ_MODEL_2", "openai/gpt-oss-120b")

JUDGE_PROMPT = """Bạn là một chuyên gia đánh giá chất lượng AI. Hãy chấm điểm câu trả lời của AI dựa trên Ground Truth.

Tiêu chí chấm điểm (thang 1-5):
- 5: Hoàn toàn chính xác, đầy đủ, chuyên nghiệp
- 4: Phần lớn chính xác, thiếu một vài chi tiết nhỏ
- 3: Đúng một phần, còn thiếu thông tin quan trọng
- 2: Sai lệch đáng kể so với Ground Truth
- 1: Hoàn toàn sai hoặc không liên quan / hallucination

Câu hỏi: {question}
Ground Truth: {ground_truth}
Câu trả lời của AI: {answer}

Trả về JSON với format (không có text ngoài JSON):
{{"score": <số nguyên 1-5>, "reasoning": "<giải thích ngắn gọn>"}}
"""


def _parse_score(raw: str) -> tuple[int, str]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    parsed  = json.loads(raw)
    score   = max(1, min(5, int(parsed["score"])))
    reason  = parsed.get("reasoning", "")
    return score, reason


class LLMJudge:
    def __init__(self):
        self._groq = None

    def _get_groq(self):
        if self._groq is None:
            from groq import Groq
            self._groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
        return self._groq

    def _call_judge(self, prompt: str, model: str) -> tuple[int, str]:
        groq = self._get_groq()
        resp = groq.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=256,
        )
        return _parse_score(resp.choices[0].message.content)

    async def evaluate_multi_judge(
        self, question: str, answer: str, ground_truth: str
    ) -> Dict[str, Any]:
        """
        Call both judges concurrently via Groq.
        Returns final_score, agreement_rate, individual_scores, conflict flag.
        """
        prompt = JUDGE_PROMPT.format(
            question=question,
            ground_truth=ground_truth,
            answer=answer,
        )

        loop = asyncio.get_event_loop()
        j1_task = loop.run_in_executor(None, self._call_judge, prompt, GROQ_MODEL)
        j2_task = loop.run_in_executor(None, self._call_judge, prompt, GROQ_MODEL_2)

        (score_1, reason_1), (score_2, reason_2) = await asyncio.gather(j1_task, j2_task)

        diff     = abs(score_1 - score_2)
        conflict = diff > 1
        avg      = (score_1 + score_2) / 2

        return {
            "final_score":    avg,
            "agreement_rate": 0.0 if conflict else 1.0,
            "conflict":       conflict,
            "individual_scores": {
                GROQ_MODEL:   score_1,
                GROQ_MODEL_2: score_2,
            },
            "reasoning": {
                GROQ_MODEL:   reason_1,
                GROQ_MODEL_2: reason_2,
            },
        }

    async def check_position_bias(
        self, question: str, response_a: str, response_b: str, ground_truth: str
    ) -> Dict[str, Any]:
        result_ab = await self.evaluate_multi_judge(question, response_a, ground_truth)
        result_ba = await self.evaluate_multi_judge(question, response_b, ground_truth)
        delta     = abs(result_ab["final_score"] - result_ba["final_score"])
        return {
            "bias_detected": delta > 0.5,
            "score_delta":   delta,
            "ab_score":      result_ab["final_score"],
            "ba_score":      result_ba["final_score"],
        }
