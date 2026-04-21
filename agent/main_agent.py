"""
Real RAG Agent using ChromaDB + HuggingFace embeddings + NVIDIA NIM LLM.
V1: top-3 retrieval, basic prompt.
V2: top-3 retrieval, improved system prompt (stay-grounded instruction).
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
CHROMA_COLLECTION  = os.getenv("CHROMA_COLLECTION_NAME", "GSM_Collection")
HF_MODEL           = os.getenv("HF_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
NVIDIA_MODEL       = os.getenv("NVIDIA_MODEL", "gpt-4-32k-0613")
NVIDIA_BASE_URL    = "https://integrate.api.nvidia.com/v1"

# ── Shared singletons — initialized in main thread to avoid thread-safety issues ──
import chromadb
from sentence_transformers import SentenceTransformer

_embed_model: SentenceTransformer | None = None
_chroma_col = None


def _get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(HF_MODEL)
    return _embed_model


def _get_collection():
    global _chroma_col
    if _chroma_col is None:
        client = chromadb.PersistentClient(path=str(ROOT / CHROMA_PERSIST_DIR))
        _chroma_col = client.get_collection(CHROMA_COLLECTION)
    return _chroma_col


def warm_up():
    """Call once from the main thread before running async tasks."""
    _get_embed_model()
    _get_collection()


# ── System prompts ────────────────────────────────────────────────────────────
_SYSTEM_V1 = (
    "Bạn là trợ lý hỗ trợ khách hàng của Xanh SM. "
    "Hãy trả lời câu hỏi dựa trên thông tin được cung cấp."
)

_SYSTEM_V2 = (
    "Bạn là trợ lý hỗ trợ khách hàng chuyên nghiệp của Xanh SM. "
    "CHỈ trả lời dựa trên thông tin trong [CONTEXT] được cung cấp. "
    "Nếu thông tin không có trong context, hãy nói rõ: 'Tôi không có thông tin về vấn đề này.' "
    "Trả lời ngắn gọn, lịch sự và chuyên nghiệp bằng tiếng Việt."
)


class MainAgent:
    def __init__(self, version: str = "v1"):
        assert version in ("v1", "v2"), "version must be 'v1' or 'v2'"
        self.version       = version
        self.name          = f"XanhSM-SupportAgent-{version.upper()}"
        self.system_prompt = _SYSTEM_V1 if version == "v1" else _SYSTEM_V2
        self._nvidia       = None

    def _get_nvidia(self):
        if self._nvidia is None:
            from openai import OpenAI
            self._nvidia = OpenAI(
                api_key=os.getenv("NVIDIA_API_KEY"),
                base_url=NVIDIA_BASE_URL,
            )
        return self._nvidia

    def _retrieve(self, question: str, top_k: int = 3) -> tuple[list[str], list[str]]:
        """Return (contexts, retrieved_ids)."""
        model      = _get_embed_model()
        collection = _get_collection()
        query_vec  = model.encode([question]).tolist()
        results    = collection.query(
            query_embeddings=query_vec,
            n_results=top_k,
            include=["documents", "metadatas"],
        )
        return results["documents"][0], results["ids"][0]

    def _generate(self, question: str, contexts: list[str]) -> tuple[str, int]:
        """Call NVIDIA NIM LLM, return (answer, tokens_used)."""
        context_text = "\n\n---\n\n".join(contexts)
        user_message = f"[CONTEXT]\n{context_text}\n\n[CÂU HỎI]\n{question}"

        resp = self._get_nvidia().chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.2,
            max_tokens=512,
        )
        answer = resp.choices[0].message.content.strip()
        tokens = resp.usage.total_tokens if resp.usage else 0
        return answer, tokens

    async def query(self, question: str) -> Dict:
        """
        RAG pipeline:
        1. Retrieve top-k chunks from ChromaDB.
        2. Generate answer with NVIDIA NIM LLM.
        """
        loop = asyncio.get_event_loop()

        contexts, retrieved_ids = await loop.run_in_executor(
            None, self._retrieve, question
        )
        answer, tokens = await loop.run_in_executor(
            None, self._generate, question, contexts
        )

        return {
            "answer":        answer,
            "contexts":      contexts,
            "retrieved_ids": retrieved_ids,
            "metadata": {
                "model":       NVIDIA_MODEL,
                "tokens_used": tokens,
                "version":     self.version,
                "sources":     retrieved_ids,
            },
        }


if __name__ == "__main__":
    agent = MainAgent(version="v1")

    async def test():
        resp = await agent.query("Làm thế nào để đặt chuyến xe trên ứng dụng?")
        print("Answer:", resp["answer"])
        print("Retrieved IDs:", resp["retrieved_ids"])

    asyncio.run(test())
