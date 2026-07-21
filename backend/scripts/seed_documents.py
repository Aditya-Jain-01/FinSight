"""One-off seed script: loops seed_filings/ folder, ingests each PDF.

Usage:
    cd backend
    python -m scripts.seed_documents

Run this against your PRODUCTION Neon connection string so the data is
live for deployment. The .env file in backend/ should have the
correct DATABASE_URL.
"""

import asyncio
import re
import sys
from pathlib import Path

# Ensure the backend app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, text
from app.database import async_session_maker
from app.models.document import Document
from app.services.ingestion_service import ingest_document


# Map filename keywords to tickers.
# Keys are matched case-insensitively against the PDF filename.
TICKER_MAP = {
    "reliance": "RELIANCE.NS",
    "tcs": "TCS.NS",
    "infosys": "INFY.NS",
    "infy": "INFY.NS",
    "hdfc": "HDFCBANK.NS",
    "hdfcbank": "HDFCBANK.NS",
    "icici": "ICICIBANK.NS",
    "wipro": "WIPRO.NS",
    "bharti": "BHARTIARTL.NS",
    "airtel": "BHARTIARTL.NS",
    "eternal": "ETERNAL.NS",
    "swiggy": "SWIGGY.NS",
    "naukri": "NAUKRI.NS",
    "nazara": "NAZARA.NS",
}

# Human-readable company name overrides for cleaner titles
_COMPANY_NAME_MAP = {
    "Hdfcbank": "HDFC Bank",
    "Eternal": "Eternal (Zomato)",
    "Naukri": "Naukri (Info Edge)",
}


def guess_ticker(filename: str) -> str | None:
    """Try to match a filename to a known ticker."""
    lower = filename.lower()
    for key, ticker in TICKER_MAP.items():
        if key in lower:
            return ticker
    return None


def make_title(filename: str) -> str:
    """Convert a seed filing filename into a readable title.
    
    Parses the standard BSE/NSE naming pattern:
      AR_{code}_{COMPANY}_{year1}_{year2}_A_{suffix}.pdf
    
    Falls back to a generic title-case conversion.
    """
    stem = Path(filename).stem
    match = re.match(r'AR_\d+_(\w+)_(\d{4})_(\d{4})', stem)
    if match:
        company_raw = match.group(1).title()
        company = _COMPANY_NAME_MAP.get(company_raw, company_raw)
        year1 = match.group(2)
        year2 = match.group(3)
        return f"{company} Annual Report {year1}-{year2}"
    # Fallback: replace underscores and hyphens with spaces, title-case
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

    results = []  # Collect (title, status, chunk_count) for summary

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
                results.append((doc.title, doc.status, doc.chunk_count))
                print()
            except Exception as e:
                print(f"   ❌ Failed: {e}\n")
                results.append((title, "exception", 0))
                # Don't stop the whole script for one bad PDF
                continue

    # Print summary table
    print("\n" + "=" * 70)
    print("📊 INGESTION SUMMARY")
    print("=" * 70)
    print(f"{'Title':<45} {'Status':<10} {'Chunks':>6}")
    print("-" * 70)
    for title, status, count in results:
        status_icon = {"ready": "✅", "partial": "⚠️", "error": "❌", "exception": "💥"}.get(status, "❓")
        # Truncate long titles
        display_title = title[:42] + "..." if len(title) > 45 else title
        print(f"{display_title:<45} {status_icon} {status:<8} {count:>6}")
    print("-" * 70)

    ready = sum(1 for _, s, _ in results if s == "ready")
    partial = sum(1 for _, s, _ in results if s == "partial")
    failed = sum(1 for _, s, _ in results if s in ("error", "exception"))
    print(f"Ready: {ready}  |  Partial: {partial}  |  Failed: {failed}  |  Total: {len(results)}")
    print("=" * 70)

    # Query the database for the final state
    async with async_session_maker() as session:
        result = await session.execute(
            text("SELECT title, status, chunk_count FROM documents ORDER BY title")
        )
        rows = result.fetchall()
        if rows:
            print("\n📋 Current database state (SELECT title, status, chunk_count FROM documents):")
            for row in rows:
                print(f"   {row.title:<45} {row.status:<10} {row.chunk_count} chunks")

    print("\n🎉 Seeding complete!")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed())
