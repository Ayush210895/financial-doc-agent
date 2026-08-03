import json
import os
import sqlite3
from anthropic import Anthropic
from retrieval import load_index_and_metadata, retrieve

DB_PATH = "data/db/financial_data.db"
TICKERS = ["JPM", "GS", "BAC", "WFC", "UBS"]

SCHEMA_DESCRIPTION = """
Tables in financial_data.db:

financial_facts(tag TEXT, start_date TEXT, end_date TEXT, value REAL, fiscal_year INTEGER,
                 fiscal_period TEXT, form TEXT, ticker TEXT)
  - tag: one of Revenues, NetIncomeLoss, EarningsPerShareBasic, Assets, StockholdersEquity
  - value is in USD (or USD/shares for EarningsPerShareBasic)
  - NOTE: the same tag/end_date can hold quarterly, 9-month, and annual cumulative values.
    The duration each row covers is julianday(end_date) - julianday(start_date), in days:
    ~90 = single quarter, ~180 = half-year YTD, ~270 = 9-month YTD, ~364-365 = full year.
  - IMPORTANT: some tags (notably Revenues, for large banks) are only filed as an ANNUAL
    figure in recent years — there may be no ~90-day row at all for a recent period, even
    though older years do have quarterly rows. Do NOT filter to ~90-day rows and assume
    that's "the most recent data" — if the most recent rows for a tag are all ~365-day
    annual figures, that IS the most recent available data. Always check the actual
    duration of whatever row you retrieve and explicitly state whether the number you're
    reporting is quarterly, YTD, or annual — never silently report a fallback to an
    older quarterly value from years earlier as if it were current.
  - Safe pattern: first query ORDER BY end_date DESC with no duration filter to see what's
    actually available for the most recent periods, then decide how to describe it.
  - UBS has no rows in this table (IFRS filer, not US-GAAP).

price_history(Date TEXT, Open REAL, High REAL, Low REAL, Close REAL, Volume INTEGER, ticker TEXT)
  - ~2 years of daily price history, all 5 tickers.

Only SELECT statements are allowed. Always filter by ticker when the question names a specific company.
"""

SYSTEM_PROMPT = f"""You are a financial research assistant covering 5 companies: {", ".join(TICKERS)}.

You have two tools:
1. search_filings — semantic search over 10-K/20-F narrative text (risk factors, business description, management discussion). Use for qualitative/narrative questions. Pass tickers explicitly whenever the question names specific companies, to avoid retrieving the wrong company's text.
2. query_financials — read-only SQL over structured financial data (reported revenue/net income/EPS/assets/equity, and daily stock prices). Use for any question involving specific numbers, growth, or comparisons.

{SCHEMA_DESCRIPTION}

For questions that need both a number and a narrative explanation, call both tools before answering.
Always cite which ticker(s) and source each part of your answer comes from. If a tool returns no relevant data, say so explicitly rather than guessing.

STRICT GROUNDING RULE (applies to numbers, names, quotes, and any specific claim):
- Every specific dollar figure, percentage, growth rate, program/initiative name, direct quote, or
  factual claim you state MUST appear verbatim or be directly and unambiguously supported by a tool
  result already returned in this conversation. Do not compute, round, blend, or infer a number that
  isn't directly present in a tool's output, and do not fill in plausible-sounding details (target
  ratios, initiative names, specific figures) from general knowledge just because they're the kind
  of thing a bank's filing would typically say. If you are not certain a specific claim came from
  the tool results in front of you, leave it out.
- search_filings returns short excerpts, not full documents. If the excerpts you retrieved are
  fragmentary or don't fully cover what the question asks, say so explicitly ("the retrieved
  excerpts don't provide detail on X") rather than writing a complete, well-organized answer that
  goes beyond what the excerpts actually contain. A shorter, honestly-incomplete answer is correct
  behavior here, not a failure.
- If both query_financials and search_filings returned numbers relevant to the question (e.g. a
  segment figure from search_filings and a company-total figure from query_financials), you must
  keep them clearly separate and correctly labeled by scope (e.g. "firm-wide revenue" vs.
  "Investment Banking segment revenue") — never substitute one for the other.
- Before writing your final answer, re-check each specific claim you are about to state against the
  exact tool_result content it came from. If you cannot point to the exact tool result a claim came
  from, do not include it — say the data wasn't available instead.
- When query_financials returns a value, prefer it over any number implied by search_filings text
  for the same concept, since the SQL data is the authoritative structured source.

TIMEFRAME DISCIPLINE:
- If a question specifies a relative timeframe ("the past year," "last quarter," "this month"),
  your query_financials SQL must filter to that actual date range (e.g. WHERE Date >= date('now',
  '-1 year')), not just fetch all available rows and describe whatever span happens to come back.
- If the data you retrieved covers a different span than what was asked (e.g. you only have ~2
  years of history and can't isolate exactly "the past year" precisely), explicitly state the
  actual date range your answer is based on, rather than silently answering about a different
  period than the one asked about.
"""

TOOLS = [
    {
        "name": "search_filings",
        "description": "Semantic search over 10-K/20-F filing text for narrative/qualitative content (risk factors, business description, strategy).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "tickers": {
                    "type": "array",
                    "items": {"type": "string", "enum": TICKERS},
                    "description": "Restrict results to these tickers. Omit to search across all companies.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "query_financials",
        "description": "Run a read-only SQL SELECT query against the structured financial database (financial_facts, price_history tables).",
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "A single SELECT statement."}
            },
            "required": ["sql"],
        },
    },
]


def query_financials(sql):
    sql_stripped = sql.strip().rstrip(";")
    if not sql_stripped.lower().startswith("select"):
        return {"error": "Only SELECT statements are allowed."}
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql_stripped)
        rows = [dict(r) for r in cursor.fetchmany(50)]
        conn.close()
        return {"rows": rows, "row_count": len(rows)}
    except Exception as e:
        return {"error": str(e)}


def run_agent(question, index, metadata, client, max_turns=5):
    messages = [{"role": "user", "content": question}]
    trace = []

    for _ in range(max_turns):
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            final_text = "".join(b.text for b in response.content if b.type == "text")
            return final_text, trace

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            if block.name == "search_filings":
                result = retrieve(
                    block.input["query"], index, metadata,
                    tickers=block.input.get("tickers"), top_k=5,
                )
                trace.append({
                    "tool": "search_filings",
                    "input": block.input,
                    "n_results": len(result),
                    "result": [{"ticker": r["ticker"], "text": r["text"][:400]} for r in result],
                })
                content = json.dumps([{"ticker": r["ticker"], "text": r["text"], "rerank_score": r.get("rerank_score")} for r in result])
            elif block.name == "query_financials":
                result = query_financials(block.input["sql"])
                trace.append({"tool": "query_financials", "input": block.input, "result": result})
                content = json.dumps(result)
            else:
                content = json.dumps({"error": f"unknown tool {block.name}"})

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": content,
            })
        messages.append({"role": "user", "content": tool_results})

    return "Max turns reached without a final answer.", trace


if __name__ == "__main__":
    index, metadata = load_index_and_metadata()
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    test_questions = [
        "What was JPMorgan's revenue growth last quarter, and what did management say drove it?",
        "Compare JPMorgan and Bank of America's approach to credit risk in their most recent filings.",
    ]

    for q in test_questions:
        print("QUESTION:", q)
        answer, trace = run_agent(q, index, metadata, client)
        print("\nANSWER:\n", answer)
        print("\nTOOL CALLS:")
        for t in trace:
            print(" -", t["tool"], t["input"])
        print("\n" + "=" * 80 + "\n")
