import json
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer, CrossEncoder

INDEX_PATH = Path("data/db/faiss_index.bin")
METADATA_PATH = Path("data/db/chunk_metadata.json")
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_embed_model = None
_reranker = None

def get_embed_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBED_MODEL_NAME)
    return _embed_model

def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANK_MODEL_NAME)
    return _reranker

def load_index_and_metadata():
    index = faiss.read_index(str(INDEX_PATH))
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    return index, metadata

def retrieve(query, index, metadata, tickers=None, top_k=5, fetch_k=30, rerank=True):
    """Two-stage retrieval: FAISS over-fetch -> optional ticker filter -> cross-encoder rerank -> top_k."""
    embed_model = get_embed_model()
    query_vec = embed_model.encode([query], convert_to_numpy=True)
    faiss.normalize_L2(query_vec)
    scores, indices = index.search(query_vec, fetch_k)

    candidates = []
    for score, idx in zip(scores[0], indices[0]):
        chunk = metadata[idx]
        if tickers and chunk["ticker"] not in tickers:
            continue
        candidates.append({**chunk, "faiss_score": float(score)})

    if not candidates:
        return []

    if rerank:
        reranker = get_reranker()
        pairs = [[query, c["text"]] for c in candidates]
        rerank_scores = reranker.predict(pairs)
        for c, s in zip(candidates, rerank_scores):
            c["rerank_score"] = float(s)
        candidates.sort(key=lambda c: c["rerank_score"], reverse=True)
    else:
        candidates.sort(key=lambda c: c["faiss_score"], reverse=True)

    return candidates[:top_k]