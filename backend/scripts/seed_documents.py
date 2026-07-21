"""One-off seed script: loops seed_filings/ folder, ingests each PDF.

Usage:
    cd backend
    python -m scripts.seed_documents

Run this against your PRODUCTION Neon connection string so the data is
live for Day 4 deployment. The .env file in backend/ should have the
correct DATABASE_URL.
"""

import asyncio
import sys
from pathlib import Path

# Ensure the backend app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import async_session_maker
from app.services.ingestion_service import ingest_document


# Map filenames (or partial names) to tickers.
# Update this dict to match your actual seed PDF filenames.
TICKER_MAP = {
    "reliance": "RELIANCE.NS",
    "tcs": "TCS.NS",
    "infosys": "INFY.NS",
    "infy": "INFY.NS",
    "hdfc": "HDFCBANK.NS",
    "icici": "ICICIBANK.NS",
    "wipro": "WIPRO.NS",
    "bharti": "BHARTIARTL.NS",
    "airtel": "BHARTIARTL.NS",
}


def guess_ticker(filename: str) -> str | None:
    """Try to match a filename to a known ticker."""
    lower = filename.lower()
    for key, ticker in TICKER_MAP.items():
        if key in lower:
            return ticker
    return None


def make_title(filename: str) -> str:
    """Convert a filename into a readable title."""
    stem = Path(filename).stem
    # Replace underscores and hyphens with spaces, title-case it
    return stem.replace("_", " ").replace("-", " ").title()


async def seed():
    seed_dir = Path(__file__).resolve().parent.parent.parent / "seed_filings"

    if not seed_dir.exists():
        print(f"❌ seed_filings/ directory not found at {seed_dir}")
        print("   Place your annual report PDFs there and re-run.")
        return

    pdf_files = sorted(seed_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ No PDF files found in {seed_dir}")
        return

    print(f"📂 Found {len(pdf_files)} PDFs in {seed_dir}\n")

    async with async_session_maker() as session:
        for pdf_path in pdf_files:
            ticker = guess_ticker(pdf_path.name)
            title = make_title(pdf_path.name)

            print(f"📄 Ingesting: {pdf_path.name}")
            print(f"   Ticker: {ticker or '(unknown)'}")
            print(f"   Title:  {title}")

            try:
                doc = await ingest_document(
                    session,
                    file_path=pdf_path,
                    ticker=ticker,
                    title=title,
                    source="seed",
                )
                print(f"   ✅ Done — {doc.chunk_count} chunks, doc_id={doc.id}\n")
            except Exception as e:
                print(f"   ❌ Failed: {e}\n")
                # Don't stop the whole script for one bad PDF
                continue

    print("🎉 Seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed())
