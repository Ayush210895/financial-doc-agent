import yfinance as yf
import pandas as pd

TICKERS = ["JPM", "GS", "BAC", "WFC", "UBS"]

def get_surprise_data(ticker, limit=20):
    t = yf.Ticker(ticker)
    df = t.get_earnings_dates(limit=limit)
    df = df.reset_index()
    df["Earnings Date"] = pd.to_datetime(df["Earnings Date"]).dt.tz_localize(None)
    df["ticker"] = ticker
    return df[["ticker", "Earnings Date", "Surprise(%)"]].dropna(subset=["Surprise(%)"])

def match_nearest_surprise(target_df, surprise_df, tolerance_days=3):
    target_df = target_df.copy()
    target_df["earnings_date"] = pd.to_datetime(target_df["earnings_date"])
    target_df["surprise_pct"] = None

    for idx, row in target_df.iterrows():
        candidates = surprise_df[surprise_df["ticker"] == row["ticker"]].copy()
        if candidates.empty:
            continue
        candidates["diff_days"] = (candidates["Earnings Date"] - row["earnings_date"]).abs().dt.days
        best = candidates[candidates["diff_days"] <= tolerance_days].sort_values("diff_days")
        if not best.empty:
            target_df.at[idx, "surprise_pct"] = best.iloc[0]["Surprise(%)"]

    return target_df

if __name__ == "__main__":
    target_df = pd.read_csv("data/processed/regression_dataset.csv")

    all_surprise = pd.concat([get_surprise_data(t) for t in TICKERS], ignore_index=True)
    print(f"Pulled surprise data: {len(all_surprise)} rows across {all_surprise['ticker'].nunique()} tickers")

    matched_df = match_nearest_surprise(target_df, all_surprise)
    print(matched_df[["ticker", "earnings_date", "surprise_pct", "price_reaction_pct"]])
    print(f"\nMatched: {matched_df['surprise_pct'].notna().sum()} / {len(matched_df)} rows")

    matched_df.to_csv("data/processed/regression_dataset_v2.csv", index=False)