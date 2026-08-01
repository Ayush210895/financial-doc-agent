# Financial Document Intelligence Agent

An agentic AI system for financial Q&A over JPM, GS, BAC, and WFC — combining
retrieval-augmented generation (RAG) over unstructured filings (10-Ks, earnings
call transcripts) with structured financial data (XBRL, price history) via a
router/tool-calling architecture, backed by an evaluation harness and deployed
as a containerized cloud service.

## Status
Actively in development. See build log for progress.

## Stack
Python, PyTorch/scikit-learn, Anthropic Claude API, FAISS/Chroma, FastAPI,
Docker, AWS, GitHub Actions.