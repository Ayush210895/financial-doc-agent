import sys
import sqlite3
import pandas as pd
import yfinance as yf
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(SRC_DIR))

DB_PATH = "data/db/financial_data.db"
TICKERS = ["JPM", "GS", "BAC", "WFC", "UBS"]

def get_earnings_events(ticker, limit=12):
    t = yf.Ticker(ticker)
    df = t.get_earnings_dates(limit=limit)
    df = df.reset_index()
    df["Earnings Date"] = pd.to_datetime(df["Earnings Date"]).dt.tz_localize(None)
    df = df.dropna(subset=["Reported EPS"])  # only actual, already-reported earnings
    df["ticker"] = ticker
    return df[["ticker", "Earnings Date", "EPS Estimate", "Reported EPS", "Surprise(%)"]]

def load_price_history(ticker, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM price_history WHERE ticker = ?", conn, params=(ticker,))
    conn.close()
    df["Date"] = pd.to_datetime(df["Date"], utc=True).dt.tz_localize(None)
    return df.sort_values("Date").reset_index(drop=True)

def compute_reaction(price_df, earnings_date):
    before = price_df[price_df["Date"] < earnings_date]
    after = price_df[price_df["Date"] > earnings_date]
    if before.empty or after.empty:
        return None
    return (after.iloc[0]["Close"] - before.iloc[-1]["Close"]) / before.iloc[-1]["Close"] * 100

if __name__ == "__main__":
    rows = []
    for ticker in TICKERS:
        events = get_earnings_events(ticker)
        price_df = load_price_history(ticker)
        for _, ev in events.iterrows():
            reaction = compute_reaction(price_df, ev["Earnings Date"])
            if reaction is not None:
                rows.append({
                    "ticker": ticker,
                    "earnings_date": ev["Earnings Date"].date(),
                    "eps_estimate": ev["EPS Estimate"],
                    "reported_eps": ev["Reported EPS"],
                    "surprise_pct": ev["Surprise(%)"],
                    "price_reaction_pct": reaction,
                })

    df = pd.DataFrame(rows)
    print(df)
    print(f"\n{len(df)} rows across {df['ticker'].nunique()} tickers")
    df.to_csv("data/processed/regression_target_v2.csv", index=False)