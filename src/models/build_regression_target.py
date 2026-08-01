import sys
import sqlite3
import pandas as pd
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(SRC_DIR))

from ingestion.edgar_client import get_recent_fillings, get_earnings_exhibit
from ingestion.xbrl_client import TICKER_CIKS

DB_PATH = "data/db/financial_data.db"

def get_earnings_dates(cik, report_form="8-K", max_quarters=8, max_check=40):
    reports = get_recent_fillings(cik, form_type=report_form)
    dates = []
    for filing in reports[:max_check]:
        exhibit = get_earnings_exhibit(cik, filing["accession_number"])
        if exhibit:
            dates.append(filing["filing_date"])
        if len(dates) >= max_quarters:
            break
    return dates

def load_price_history(ticker, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        "SELECT * FROM price_history WHERE ticker = ?", conn, params=(ticker,)
    )
    conn.close()
    df["Date"] = pd.to_datetime(df["Date"], utc=True).dt.tz_localize(None)
    df = df.sort_values("Date").reset_index(drop=True)
    return df

def compute_reaction(price_df, earnings_date):
    earnings_date = pd.Timestamp(earnings_date)
    before = price_df[price_df["Date"] < earnings_date]
    after = price_df[price_df["Date"] > earnings_date]
    if before.empty or after.empty:
        return None
    pre_price = before.iloc[-1]["Close"]
    post_price = after.iloc[0]["Close"]
    pct_change = (post_price - pre_price) / pre_price * 100
    return pct_change

if __name__ == "__main__":
    rows = []
    for ticker, cik in TICKER_CIKS.items():
        report_form = "6-K" if ticker == "UBS" else "8-K"
        dates = get_earnings_dates(cik, report_form=report_form)
        print(f"{ticker}: {len(dates)} earnings dates found -> {dates}")

        price_df = load_price_history(ticker)
        for d in dates:
            reaction = compute_reaction(price_df, d)
            if reaction is not None:
                rows.append({"ticker": ticker, "earnings_date": d, "price_reaction_pct": reaction})

    result_df = pd.DataFrame(rows)
    print(result_df)
    result_df.to_csv("data/processed/regression_target.csv", index=False)
    print(f"\nSaved {len(result_df)} rows to data/processed/regression_target.csv")

    print("\nSummary stats:")
    print(result_df["price_reaction_pct"].describe())
    print("\nPer-ticker mean/std:")
    print(result_df.groupby("ticker")["price_reaction_pct"].agg(["mean", "std", "count"]))