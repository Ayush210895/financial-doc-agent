import sys
import sqlite3
import pandas as pd
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(SRC_DIR))

DB_PATH = "data/db/financial_data.db"
FEATURE_TAGS = ["Revenues", "NetIncomeLoss", "EarningsPerShareBasic"]

def load_financial_facts(ticker, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM financial_facts WHERE ticker = ?", conn, params=(ticker,))
    conn.close()
    df["end_date"] = pd.to_datetime(df["end_date"])
    return df

def get_features_for_date(facts_df, earnings_date, tags=FEATURE_TAGS):
    earnings_date = pd.Timestamp(earnings_date)
    features = {}

    facts_df = facts_df.copy()
    facts_df["start_date"] = pd.to_datetime(facts_df["start_date"])
    facts_df["duration_days"] = (facts_df["end_date"] - facts_df["start_date"]).dt.days

    for tag in tags:
        tag_df = facts_df[
            (facts_df["tag"] == tag) &
            (facts_df["duration_days"] >= 80) &
            (facts_df["duration_days"] <= 100)
        ].sort_values("end_date")

        prior = tag_df[tag_df["end_date"] <= earnings_date]
        if prior.empty:
            features[f"{tag}_latest"] = None
            features[f"{tag}_growth_qoq"] = None
            continue

        latest_value = prior.iloc[-1]["value"]
        features[f"{tag}_latest"] = latest_value

        if len(prior) >= 2:
            previous_value = prior.iloc[-2]["value"]
            if previous_value != 0:
                features[f"{tag}_growth_qoq"] = (latest_value - previous_value) / abs(previous_value)
            else:
                features[f"{tag}_growth_qoq"] = None
        else:
            features[f"{tag}_growth_qoq"] = None

    return features

if __name__ == "__main__":
    target_df = pd.read_csv("data/processed/regression_target.csv")

    rows = []
    for ticker in target_df["ticker"].unique():
        facts_df = load_financial_facts(ticker)
        ticker_events = target_df[target_df["ticker"] == ticker]
        for _, event in ticker_events.iterrows():
            features = get_features_for_date(facts_df, event["earnings_date"])
            features["ticker"] = ticker
            features["earnings_date"] = event["earnings_date"]
            features["price_reaction_pct"] = event["price_reaction_pct"]
            rows.append(features)

    full_df = pd.DataFrame(rows)
    print(full_df)
    print(f"\nMissing values per column:\n{full_df.isnull().sum()}")
    full_df.to_csv("data/processed/regression_dataset.csv", index=False)
    print(f"\nSaved {len(full_df)} rows to data/processed/regression_dataset.csv")