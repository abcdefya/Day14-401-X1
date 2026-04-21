"""
Chunking & Embedding Pipeline for XanhSM FAQ documents.
Splits markdown files by ## headers, embeds with HuggingFace, stores in ChromaDB.
Run: python data/ingest.py
"""
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── resolve project root so imports work when run from any directory ──────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
CHROMA_COLLECTION  = os.getenv("CHROMA_COLLECTION_NAME", "GSM_Collection")
HF_MODEL           = os.getenv("HF_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
DATA_DIR           = Path(os.getenv("DATA_DIR", "./data")) / "GSM"

# file-slug mapping (deterministic chunk-id prefix)
FILE_SLUG = {
    "XanhSM - User FAQs.md":                 "user_faq",
    "XanhSM - electric_car_driver FAQs.md":   "car_driver_faq",
    "XanhSM - electric_motor_driver FAQs.md": "motor_driver_faq",
    "XanhSM - Restaurant FAQs.md":            "restaurant_faq",
}


def parse_markdown_chunks(filepath: Path, slug: str) -> list[dict]:
    """
    Split a markdown file into chunks on '## ' headers.
    Returns list of {id, text, source, section_title}.
    """
    text = filepath.read_text(encoding="utf-8")
    # Split on level-2 headers (## X.X. ...)
    parts = re.split(r"\n(?=## )", text)

    chunks = []
    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Extract section number from header line, e.g. "## 1.2. Title"
        header_match = re.match(r"## (\d+\.\d+)\.\s*(.*)", part)
        if header_match:
            section_num   = header_match.group(1)   # "1.2"
            section_title = header_match.group(2).strip()
            chunk_id = f"{slug}_{section_num}"
        else:
            # Preamble text before first ## header — skip or assign slug_0
            if len(part) < 30:
                continue
            chunk_id      = f"{slug}_intro"
            section_title = "Introduction"

        chunks.append({
            "id":            chunk_id,
            "text":          part,
            "source":        filepath.name,
            "section_title": section_title,
        })

    return chunks


def build_vector_store(chunks: list[dict]):
    """Embed all chunks and upsert into ChromaDB."""
    import chromadb
    from sentence_transformers import SentenceTransformer  # noqa: F401 (already imported at module level in agent)

    print(f"Loading embedding model: {HF_MODEL}")
    model = SentenceTransformer(HF_MODEL)

    print(f"Connecting to ChromaDB at {CHROMA_PERSIST_DIR}")
    client = chromadb.PersistentClient(path=str(ROOT / CHROMA_PERSIST_DIR))

    # Delete existing collection so re-runs are idempotent
    try:
        client.delete_collection(CHROMA_COLLECTION)
        print(f"Deleted existing collection '{CHROMA_COLLECTION}'")
    except Exception:
        pass

    collection = client.create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    ids        = [c["id"]   for c in chunks]
    texts      = [c["text"] for c in chunks]
    metadatas  = [{"source": c["source"], "section_title": c["section_title"]} for c in chunks]

    print(f"Embedding {len(chunks)} chunks …")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32).tolist()

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    print(f"✅ Stored {len(chunks)} chunks in collection '{CHROMA_COLLECTION}'")
    return collection


def main():
    all_chunks: list[dict] = []

    for filename, slug in FILE_SLUG.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f"⚠️  File not found: {filepath}")
            continue
        chunks = parse_markdown_chunks(filepath, slug)
        print(f"  {filename}: {len(chunks)} chunks")
        all_chunks.extend(chunks)

    print(f"\nTotal chunks: {len(all_chunks)}")
    build_vector_store(all_chunks)
    print("\n✅ Ingestion complete. Run 'python data/synthetic_gen.py' next.")


if __name__ == "__main__":
    main()
