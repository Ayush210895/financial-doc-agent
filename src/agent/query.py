import json
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from pathlib import Path
from anthropic import Anthropic

INDEX_PATH = Path("data/db/faiss_index.bin")
METADATA_PATH = Path("data/db/chunk_metadata.json")
MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 5

def load_index_and_metadata():
    index = faiss.read_index(str(INDEX_PATH))
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    return index, metadata

def retrieve(query, index, metadata, model, top_k=TOP_K):
    query_vec = model.encode([query], convert_to_numpy=True)
    faiss.normalize_L2(query_vec)
    scores, indices = index.search(query_vec, top_k)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        chunk = metadata[idx]
        results.append({**chunk, "score": float(score)})
    return results

def build_prompt(query, chunks):
    context = "\n\n---\n\n".join(
        f"[Source: {c['ticker']}, {c['source_file']}]\n{c['text']}" for c in chunks
    )
    return f"""You are a financial analyst assistant. Answer the question using ONLY the context below. If the context doesn't contain the answer, say so explicitly. Cite the ticker for any claim you make.

Context:
{context}

Question: {query}

Answer:"""

def ask(query, index, metadata, model, client):
    chunks = retrieve(query, index, metadata, model)
    prompt = build_prompt(query, chunks)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text, chunks

if __name__ == "__main__":
    index, metadata = load_index_and_metadata()
    model = SentenceTransformer(MODEL_NAME)
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    test_queries = [
        "What are JPMorgan's main risk factors related to interest rates?",
        "Compare JPMorgan and Bank of America's approach to credit risk in their most recent filings.",
        "What was JPMorgan's net income and how did management explain the change?",
    ]

    for test_query in test_queries:
        answer, sources = ask(test_query, index, metadata, model, client)
        print("QUESTION:", test_query)
        print("\nANSWER:\n", answer)
        print("\nSOURCES USED:")
        for s in sources:
            print(f"  - {s['ticker']} | {s['source_file']} | score={s['score']:.3f}")
        print("\n" + "="*80 + "\n")