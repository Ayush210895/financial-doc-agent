GOLDEN_SET = [
    {"id": "jpm_interest_rate_risk", "category": "narrative",
     "question": "What are JPMorgan's main risk factors related to interest rates?",
     "expected_tickers": ["JPM"]},

    {"id": "jpm_bac_credit_risk", "category": "comparison",
     "question": "Compare JPMorgan and Bank of America's approach to credit risk in their most recent filings.",
     "expected_tickers": ["JPM", "BAC"]},

    {"id": "jpm_revenue_growth", "category": "numeric",
     "question": "What was JPMorgan's total revenue in 2025 and how much did it grow from 2024?",
     "expected_tickers": ["JPM"], "expected_substrings": ["182.4", "177.5"]},

    {"id": "gs_strategy", "category": "narrative",
     "question": "What is Goldman Sachs' core business strategy according to its most recent annual report?",
     "expected_tickers": ["GS"]},

    {"id": "wfc_risk_factors", "category": "narrative",
     "question": "What are Wells Fargo's main risk factors related to regulatory compliance?",
     "expected_tickers": ["WFC"]},

    {"id": "ubs_business", "category": "narrative",
     "question": "What is UBS's core business strategy according to its most recent annual report?",
     "expected_tickers": ["UBS"]},

    {"id": "gs_bac_wfc_comparison", "category": "comparison",
     "question": "Compare how Goldman Sachs, Bank of America, and Wells Fargo describe their approach to market risk.",
     "expected_tickers": ["GS", "BAC", "WFC"]},

    {"id": "jpm_net_income", "category": "numeric",
     "question": "What was JPMorgan's net income in 2025?",
     "expected_tickers": ["JPM"]},

    {"id": "jpm_eps", "category": "numeric",
     "question": "What was JPMorgan's basic earnings per share in 2025?",
     "expected_tickers": ["JPM"]},

    {"id": "bac_assets", "category": "numeric",
     "question": "What were Bank of America's total assets as of the most recent reporting period?",
     "expected_tickers": ["BAC"]},

    {"id": "ubs_xbrl_gap", "category": "abstention",
     "question": "What was UBS's net income according to its US-GAAP XBRL filings?",
     "expected_tickers": ["UBS"], "expect_abstention": True},

    {"id": "jpm_price_trend", "category": "numeric",
     "question": "How has JPMorgan's stock price trended over the past year based on the closing prices in the database?",
     "expected_tickers": ["JPM"]},

    {"id": "gs_wfc_credit", "category": "comparison",
     "question": "Compare Goldman Sachs and Wells Fargo's exposure to consumer versus wholesale credit risk.",
     "expected_tickers": ["GS", "WFC"]},

    {"id": "out_of_scope", "category": "abstention",
     "question": "What was Tesla's revenue in 2025?",
     "expected_tickers": [], "expect_abstention": True},

    {"id": "jpm_stockholders_equity", "category": "numeric",
     "question": "What was JPMorgan's stockholders' equity as of the most recent reporting period?",
     "expected_tickers": ["JPM"]},
]