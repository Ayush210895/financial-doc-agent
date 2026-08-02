from pathlib import Path
import json

TEXT_DIR = Path("data/processed/filings_text")
OUT_DIR = Path("data/processed/chunks")
OUT_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 1000
OVERLAP = 150

def load_paragraphs(text_path):
    text = text_path.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]
    return lines

def chunk_lines(lines, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    chunks = []
    current = ""
    for line in lines:
        if len(current) + len(line) + 1 > chunk_size and current:
            chunks.append(current.strip())
            # start next chunk with the tail of the previous one, for overlap
            current = current[-overlap:] + "\n" + line
        else:
            current += "\n" + line
    if current.strip():
        chunks.append(current.strip())
    return chunks

if __name__ == "__main__":
    all_chunks = []
    for text_file in TEXT_DIR.glob("*.txt"):
        ticker = text_file.stem.split("_")[0]
        lines = load_paragraphs(text_file)
        chunks = chunk_lines(lines)
        print(f"{text_file.name}: {len(lines)} lines -> {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "ticker": ticker,
                "source_file": text_file.name,
                "chunk_id": f"{ticker}_{i}",
                "text": chunk,
            })

    out_path = OUT_DIR / "all_chunks.json"
    out_path.write_text(json.dumps(all_chunks, indent=2), encoding="utf-8")
    print(f"\nTotal chunks: {len(all_chunks)} saved to {out_path}")