import requests
import pandas as pd
import sqlite3

HEADERS = {"User-Agent": "Ayush Soni ayushsoni1.nmims@gmail.com"}
TARGET_TAGS = ["Revenues", "NetIncomeLoss", "EarningsPerShareBasic", "Assets", "StockholdersEquity"]
DB_PATH = "data/db/financial_data.db"
TICKER_CIKS = {
    "JPM": "0000019617",
    "BAC": "0000070858",
    "GS": "0000886982",
    "WFC": "0000072971",
    "UBS": "0001610520",
}

def get_company_facts(cik):
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def extract_tag(facts, tag, unit="USD"):
    try:
        tag_data = facts["facts"]["us-gaap"][tag]
    except KeyError:
        return pd.DataFrame()  # tag doesn't exist for this company

    rows = []
    for entry in tag_data["units"].get(unit, []):
        rows.append({
            "tag": tag,
            "end_date": entry["end"],
            "value": entry["val"],
            "fiscal_year": entry.get("fy"),
            "fiscal_period": entry.get("fp"),
            "form": entry.get("form"),
        })
    return pd.DataFrame(rows)

def save_to_sqlite(df, table_name, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, if_exists="append", index=False)
    conn.close()

if __name__ == "__main__":
    unit_overrides = {"EarningsPerShareBasic": "USD/shares"}

    for ticker, cik in TICKER_CIKS.items():
        facts = get_company_facts(cik)
        all_dfs = []
        for tag in TARGET_TAGS:
            unit = unit_overrides.get(tag, "USD")
            df = extract_tag(facts, tag, unit=unit)
            if not df.empty:
                df["ticker"] = ticker
                all_dfs.append(df)

        if all_dfs:
            combined = pd.concat(all_dfs, ignore_index=True)
            save_to_sqlite(combined, "financial_facts")
            print(f"{ticker}: saved {len(combined)} rows")
        else:
            print(f"{ticker}: no XBRL data found (likely non-US-GAAP filer)")