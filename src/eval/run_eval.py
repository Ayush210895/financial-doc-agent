import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime, timezone

SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(SRC_DIR))
sys.path.append(str(SRC_DIR / "agent"))

from anthropic import Anthropic
from retrieval import load_index_and_metadata
from router import run_agent
from golden_set import GOLDEN_SET

JUDGE_MODEL = "claude-haiku-4-5-20251001"
RESULTS_DIR = Path("data/eval/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def extract_cited_tickers(trace):
    tickers = set()
    for t in trace:
        if t["tool"] == "search_filings":
            for tk in (t["input"].get("tickers") or []):
                tickers.add(tk)
        elif t["tool"] == "query_financials":
            sql = t["input"].get("sql", "")
            for tk in re.findall(r"ticker\s*=\s*'([A-Z]+)'", sql):
                tickers.add(tk)
            for group in re.findall(r"ticker\s+IN\s*\(([^)]+)\)", sql, re.IGNORECASE):
                for tk in re.findall(r"'([A-Z]+)'", group):
                    tickers.add(tk)
    return tickers


def check_ticker_grounding(item, trace, answer):
    expected = set(item.get("expected_tickers", []))
    if not expected:
        return None
    cited = extract_cited_tickers(trace)
    also_in_answer = {tk for tk in expected if tk in answer}
    covered = cited | also_in_answer
    missing = expected - covered
    return {"expected": sorted(expected), "covered": sorted(covered), "missing": sorted(missing), "pass": len(missing) == 0}


def check_substrings(item, answer):
    expected = item.get("expected_substrings")
    if not expected:
        return None
    missing = [s for s in expected if s not in answer]
    return {"expected": expected, "missing": missing, "pass": len(missing) == 0}


def llm_judge(client, question, answer, trace):
    context_dump = json.dumps([
        {"tool": t["tool"], "input": t["input"], "output": t.get("result", t.get("n_results"))}
        for t in trace
    ], default=str)[:6000]

    judge_prompt = f"""You are grading an AI financial assistant's answer for faithfulness and relevance.

Question: {question}

Tool calls and results the assistant had available:
{context_dump}

Assistant's final answer:
{answer}

Score the answer on two dimensions, 1 (poor) to 5 (excellent):
- faithfulness: are all factual claims (numbers, statements) in the answer actually supported by the tool results above? Penalize heavily if the answer states a number not present in the tool results, or misattributes a segment/partial figure as a company total.
- relevance: does the answer actually address the question asked?

Respond with ONLY a JSON object, no other text, in this exact shape:
{{"faithfulness": <1-5>, "relevance": <1-5>, "unsupported_claims": ["..."], "notes": "brief reason"}}
"""
    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": judge_prompt}],
    )
    text = response.content[0].text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return {"faithfulness": None, "relevance": None, "unsupported_claims": [], "notes": f"JUDGE PARSE FAILURE: {text[:200]}"}


def run_eval():
    index, metadata = load_index_and_metadata()
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    results = []
    for item in GOLDEN_SET:
        print(f"Running: {item['id']}...")
        answer, trace = run_agent(item["question"], index, metadata, client)

        ticker_check = check_ticker_grounding(item, trace, answer)
        substring_check = check_substrings(item, answer)
        judge = llm_judge(client, item["question"], answer, trace)

        results.append({
            "id": item["id"],
            "category": item["category"],
            "question": item["question"],
            "answer": answer,
            "ticker_check": ticker_check,
            "substring_check": substring_check,
            "judge": judge,
        })

    out_path = RESULTS_DIR / f"results_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print("\n" + "=" * 80)
    print("EVAL SUMMARY")
    print("=" * 80)
    n = len(results)
    ticker_pass = sum(1 for r in results if r["ticker_check"] and r["ticker_check"]["pass"])
    ticker_total = sum(1 for r in results if r["ticker_check"])
    substr_pass = sum(1 for r in results if r["substring_check"] and r["substring_check"]["pass"])
    substr_total = sum(1 for r in results if r["substring_check"])
    faithfulness_scores = [r["judge"]["faithfulness"] for r in results if r["judge"].get("faithfulness") is not None]
    relevance_scores = [r["judge"]["relevance"] for r in results if r["judge"].get("relevance") is not None]

    print(f"Questions run: {n}")
    print(f"Ticker/entity grounding: {ticker_pass}/{ticker_total} passed")
    print(f"Known-value substring checks: {substr_pass}/{substr_total} passed")
    if faithfulness_scores:
        print(f"Avg faithfulness (LLM judge, 1-5): {sum(faithfulness_scores)/len(faithfulness_scores):.2f}")
    if relevance_scores:
        print(f"Avg relevance (LLM judge, 1-5): {sum(relevance_scores)/len(relevance_scores):.2f}")

    print("\nPer-question:")
    for r in results:
        tflag = "PASS" if (not r["ticker_check"] or r["ticker_check"]["pass"]) else "FAIL"
        sflag = "PASS" if (not r["substring_check"] or r["substring_check"]["pass"]) else "FAIL"
        f = r["judge"].get("faithfulness")
        rel = r["judge"].get("relevance")
        print(f"  [{r['category']:10s}] {r['id']:25s} ticker={tflag} substr={sflag} faithfulness={f} relevance={rel}")

    print(f"\nFull results saved to {out_path}")
    return results


if __name__ == "__main__":
    run_eval()
