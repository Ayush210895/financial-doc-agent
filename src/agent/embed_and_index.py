import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from pathlib import Path

CHUNKS_PATH = Path("data/processed/chunks/all_chunks.json")
INDEX_PATH = Path("data/db/faiss_index.bin")
METADATA_PATH = Path("data/db/chunk_metadata.json")
MODEL_NAME = "all-MiniLM-L6-v2"

def load_chunks():
    return json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))

def build_index(chunks, model_name=MODEL_NAME):
    model = SentenceTransformer(model_name)
    texts = [c["text"] for c in chunks]
    print(f"Embedding {len(texts)} chunks with {model_name}...")
    embeddings = model.encode(texts, batch_size=64, show_progress_bar=True, convert_to_numpy=True)
    faiss.normalize_L2(embeddings)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index, embeddings

if __name__ == "__main__":
    chunks = load_chunks()
    index, embeddings = build_index(chunks)
    faiss.write_index(index, str(INDEX_PATH))
    METADATA_PATH.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
    print(f"\nIndex built: {index.ntotal} vectors, dimension {embeddings.shape[1]}")
    print(f"Saved index to {INDEX_PATH}")
    print(f"Saved metadata to {METADATA_PATH}")