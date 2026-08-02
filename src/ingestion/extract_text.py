from bs4 import BeautifulSoup
from pathlib import Path
import re

RAW_DIR = Path("data/raw/filings")
OUT_DIR = Path("data/processed/filings_text")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_text(html_path):
    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")

    for tag in soup.find_all(style=lambda v: v and "display:none" in v):
        tag.decompose()

    text = soup.get_text(separator="\n")
    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]

    # merge fragment-like lines (short, no ending punctuation) into a running paragraph
    merged_lines = []
    buffer = ""
    for line in raw_lines:
        buffer = (buffer + " " + line).strip() if buffer else line
        if re.search(r'[.!?:;)]"?$', line) or len(buffer) > 300:
            merged_lines.append(buffer)
            buffer = ""
    if buffer:
        merged_lines.append(buffer)

    return "\n".join(merged_lines)

if __name__ == "__main__":
    for html_file in RAW_DIR.glob("*.htm"):
        text = extract_text(html_file)
        out_path = OUT_DIR / (html_file.stem + ".txt")
        out_path.write_text(text, encoding="utf-8")
        print(f"{html_file.name}: {len(text):,} characters -> {out_path.name}")