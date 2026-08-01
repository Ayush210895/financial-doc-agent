import requests

HEADERS = {"User-Agent": "Ayush Soni ayushsoni1.nmims@gmail.com"}
TICKERS = {"JPM", "GS", "BAC", "WFC", "UBS"}

def get_cik_map():
    url = "https://www.sec.gov/files/company_tickers.json"
    response = requests.get(url, headers=HEADERS)
    return response.json()

def get_cik_for_ticker(cik_map, tickers):
    result = {}
    for entry in cik_map.values():
        if entry["ticker"] in tickers:
            result[entry["ticker"]] = str(entry["cik_str"]).zfill(10)
    return result

def get_recent_fillings(cik, form_type="10-K"):
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    recent = data["filings"]["recent"]

    fillings = []
    for i in range(len(recent["form"])):
        if recent["form"][i] == form_type:
            fillings.append({
                "accession_number": recent["accessionNumber"][i],
                "filing_date": recent["filingDate"][i],
                "primaryDocument": recent["primaryDocument"][i]
            })
    return fillings

def download_fillings(cik, accession_number, primary_document, save_path):
    cik_stripped = cik.lstrip("0")
    accession_no_dashes = accession_number.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_stripped}/{accession_no_dashes}/{primary_document}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(response.content)
    print(f"Saved: {save_path}")

def get_earnings_exhibit(cik, accession_number):
    cik_stripped = cik.lstrip("0")
    accession_no_dashes = accession_number.replace("-", "")
    index_url = f"https://www.sec.gov/Archives/edgar/data/{cik_stripped}/{accession_no_dashes}/index.json"
    response = requests.get(index_url, headers=HEADERS)
    response.raise_for_status()
    items = response.json()["directory"]["item"]

    for item in items:
        if "991" in item["name"].lower():
            return item["name"]
    for item in items:
        if "99" in item["name"].lower():
            return item["name"]
    return None

if __name__ == "__main__":
    cik_map = get_cik_map()
    ticker_ciks = get_cik_for_ticker(cik_map, TICKERS)
    form_types = {"UBS": "20-F"}

    # 1. Annual reports (10-K / 20-F)
    for ticker, cik in ticker_ciks.items():
        form = form_types.get(ticker, "10-K")
        filings = get_recent_fillings(cik, form_type=form)
        if not filings:
            print(f"{ticker}: no {form} found, skipping")
            continue
        latest = filings[0]
        ext = latest["primaryDocument"].split(".")[-1]
        save_path = f"data/raw/filings/{ticker}_{latest['filing_date']}.{ext}"
        download_fillings(cik, latest["accession_number"], latest["primaryDocument"], save_path)

    # 2. Earnings-release exhibits
    current_report_types = {"UBS": "6-K"}
    for ticker, cik in ticker_ciks.items():
        report_form = current_report_types.get(ticker, "8-K")
        recent_reports = get_recent_fillings(cik, form_type=report_form)
        found = False
        for filing in recent_reports[:10]:
            exhibit = get_earnings_exhibit(cik, filing["accession_number"])
            if exhibit:
                ext = exhibit.split(".")[-1]
                save_path = f"data/raw/transcripts/{ticker}_{filing['filing_date']}.{ext}"
                download_fillings(cik, filing["accession_number"], exhibit, save_path)
                found = True
                break
        if not found:
            print(f"{ticker}: no earnings exhibit found in last 10 {report_form}s")