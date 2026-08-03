import os
import sys
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI
from pydantic import BaseModel
from anthropic import Anthropic

SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(SRC_DIR))
sys.path.append(str(SRC_DIR / "agent"))

from retrieval import load_index_and_metadata
from router import run_agent

app = FastAPI(title="Financial Document Intelligence Agent")

_state: Dict[str, Any] = {}


@app.on_event("startup")
def startup():
    index, metadata = load_index_and_metadata()
    _state["index"] = index
    _state["metadata"] = metadata
    _state["client"] = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    tool_calls: List[Dict[str, Any]]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    answer, trace = run_agent(req.question, _state["index"], _state["metadata"], _state["client"])
    tool_calls = [{"tool": t["tool"], "input": t["input"]} for t in trace]
    return {"answer": answer, "tool_calls": tool_calls}
