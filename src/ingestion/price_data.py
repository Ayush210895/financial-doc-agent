import yfinance as yf
import pandas as pd
import sqlite3

TICKERS = ["JPM", "GS", "BAC", "WFC", "UBS"]
DB_PATH = "data/db/financial_data.db"

def pull_price_history(ticker, period="2y"):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    df["ticker"] = ticker
    return df

def save_to_sqlite(df, table_name, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, if_exists="append", index=True)
    conn.close()

if __name__ == "__main__":
    for ticker in TICKERS:
        df = pull_price_history(ticker)
        print(f"{ticker}: {len(df)} rows")
        save_to_sqlite(df, "price_history")