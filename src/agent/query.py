import os
from anthropic import Anthropic
from retrieval import load_index_and_metadata, retrieve

def build_prompt(query, chunks):
    context = "\n\n---\n\n".join(
        f"[Source: {c['ticker']}, {c['source_file']}]\n{c['text']}" for c in chunks
    )
    return f"""You are a financial analyst assistant. Answer the question using ONLY the context below. If the context doesn't contain the answer, say so explicitly. Cite the ticker for any claim you make.

Context:
{context}

Question: {query}

Answer:"""

def ask(query, index, metadata, client, tickers=None):
    chunks = retrieve(query, index, metadata, tickers=tickers, top_k=5)
    prompt = build_prompt(query, chunks)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text, chunks

if __name__ == "__main__":
    index, metadata = load_index_and_metadata()
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    test_query = "What are JPMorgan's main risk factors related to interest rates?"
    answer, sources = ask(test_query, index, metadata, client)

    print("QUESTION:", test_query)
    print("\nANSWER:\n", answer)
    print("\nSOURCES USED:")
    for s in sources:
        print(f"  - {s['ticker']} | {s['source_file']} | faiss={s['faiss_score']:.3f} | rerank={s.get('rerank_score', 0):.3f}")