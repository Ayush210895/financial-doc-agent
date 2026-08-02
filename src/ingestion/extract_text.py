from bs4 import BeautifulSoup
from pathlib import Path

RAW_DIR = Path("data/raw/filings")
OUT_DIR = Path("data/processed/filings_text")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_text(html_path):
    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")

    # remove hidden XBRL metadata blocks entirely
    for tag in soup.find_all(style=lambda v: v and "display:none" in v):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

if __name__ == "__main__":
    for html_file in RAW_DIR.glob("*.htm"):
        text = extract_text(html_file)
        out_path = OUT_DIR / (html_file.stem + ".txt")
        out_path.write_text(text, encoding="utf-8")
        print(f"{html_file.name}: {len(text):,} characters -> {out_path.name}")