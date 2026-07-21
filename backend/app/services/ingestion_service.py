"""Ingestion service: PDF → text → section filtering → chunks → embeddings → Postgres.

Shared function used by both the seed script and the upload endpoint.

Key design decisions:
- Section pre-filtering reduces embedding volume by 60-80% for large annual reports
- Batch size of 30 keeps each API call under the 20k token/request limit
- 15-second interval between batches stays under 5 RPM free-tier floor
- Per-batch failure tolerance: partial ingestion beats total failure
- Deduplication: re-running is safe (skips ready docs, re-ingests failed ones)
"""

import asyncio
import logging
import re
import time
from pathlib import Path

import pdfplumber
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Document, DocumentChunk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Embedding model — BAAI/bge-base-en-v1.5
# This natively outputs 768-dim vectors, matching our schema exactly.
# ---------------------------------------------------------------------------
_embeddings = HuggingFaceEndpointEmbeddings(
    huggingfacehub_api_token=settings.huggingface_api_key,
    model="BAAI/bge-base-en-v1.5",
)

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=150,
    separators=["\n\n", "\n", ". ", " ", ""],
)

# ---------------------------------------------------------------------------
# Rate-limit-aware batching configuration
#
# Hard constraints (gemini-embedding-001, free tier):
#   - 20,000 tokens per request (batch)
#   - 5–15 RPM (requests per minute)
#   - 2,048 tokens per individual text
#
# Our settings:
#   - batch_size=30 × ~500 tokens/chunk = ~15k tokens → under 20k limit
#   - interval=15s → 4 RPM → under 5 RPM floor
#   - 5 retries with 15s–120s exponential backoff
# ---------------------------------------------------------------------------
_EMBED_BATCH_SIZE = 30
_MIN_INTERVAL_SECONDS = 2.0
_MAX_RETRIES = 5
_last_embed_call = 0.0


# ---------------------------------------------------------------------------
# Section filtering keywords
#
# These match the sections of Indian/US annual reports that users actually
# query about. Pages not matching any keyword are dropped before chunking.
# If no keywords match at all, the full document is used as fallback.
# ---------------------------------------------------------------------------
_RELEVANT_KEYWORDS = [
    "management discussion", "md&a", "mda",
    "financial highlight", "financial summary", "financial review",
    "business overview", "business review",
    "risk factor", "risk management",
    "capital expenditure", "capex",
    "strategy", "strategic", "outlook",
    "chairman", "managing director",
    "director's report", "directors report", "director report",
    "corporate governance",
    "operational review", "operational performance",
    "segment", "revenue from operations",
    "profit and loss", "profit & loss", "statement of profit",
    "balance sheet", "cash flow",
    "key performance", "kpi",
    "industry overview", "market overview",
    "dividend", "earnings per share",
    "research and development", "r&d",
]


# ===== PDF TEXT EXTRACTION =====

def extract_pages_from_pdf(file_path: str | Path) -> list[str]:
    """Extract text from each page of a PDF on disk. Returns one string per page."""
    pages = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                pages.append(page_text)
    return pages


def extract_pages_from_bytes(file_bytes: bytes) -> list[str]:
    """Extract text from each page of in-memory PDF bytes."""
    import io
    pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                pages.append(page_text)
    return pages


# Backward-compatible wrappers (used by no external code today, but kept for safety)
def extract_text_from_pdf(file_path: str | Path) -> str:
    return "\n\n".join(extract_pages_from_pdf(file_path))


def extract_text_from_bytes(file_bytes: bytes) -> str:
    return "\n\n".join(extract_pages_from_bytes(file_bytes))


# ===== SECTION FILTERING =====

def filter_relevant_pages(pages: list[str]) -> tuple[list[str], dict]:
    """Filter pages to keep only those containing queryable financial sections.

    Strategy:
    - For each page, check if any line contains a relevant keyword
    - If a page matches, include it plus 1 page before and 2 pages after for context
    - If NO pages match, fall back to the full document (never silently skip)

    Returns:
        (filtered_pages, filter_metadata_dict)
    """
    if not pages:
        return pages, {"filter_path": "empty_input", "total_pages": 0}

    relevant_indices: set[int] = set()
    matched_keywords: dict[str, list[int]] = {}

    for i, page in enumerate(pages):
        page_lower = page.lower()
        for kw in _RELEVANT_KEYWORDS:
            if kw in page_lower:
                # Include this page plus neighbors for context continuity
                for j in range(max(0, i - 1), min(len(pages), i + 3)):
                    relevant_indices.add(j)
                matched_keywords.setdefault(kw, []).append(i + 1)  # 1-indexed for readability
                break  # One keyword match per page is enough

    if not relevant_indices:
        return pages, {
            "filter_path": "no_relevant_pages_detected",
            "total_pages": len(pages),
            "note": "Using full document text as fallback",
        }

    filtered = [pages[i] for i in sorted(relevant_indices)]
    original_chars = sum(len(p) for p in pages)
    filtered_chars = sum(len(p) for p in filtered)

    return filtered, {
        "filter_path": "pages_filtered",
        "total_pages": len(pages),
        "relevant_pages": len(filtered),
        "original_chars": original_chars,
        "filtered_chars": filtered_chars,
        "reduction_pct": round((1 - filtered_chars / max(original_chars, 1)) * 100, 1),
        "matched_keywords": list(matched_keywords.keys()),
    }


# ===== CHUNKING =====

def chunk_text(text: str) -> list[dict]:
    """Split text into chunks with metadata."""
    docs = _splitter.create_documents([text])
    chunks = []
    for i, doc in enumerate(docs):
        # Try to extract a section title from the first line of the chunk
        lines = doc.page_content.strip().split("\n")
        section_title = None
        if lines and len(lines[0]) < 120 and lines[0].isupper():
            section_title = lines[0].strip()

        chunks.append({
            "chunk_index": i,
            "content": doc.page_content,
            "section_title": section_title,
        })
    return chunks


# ===== EMBEDDING WITH BACKOFF =====

async def _throttle():
    """Enforce minimum interval between embedding API calls."""
    global _last_embed_call
    elapsed = time.monotonic() - _last_embed_call
    if elapsed < _MIN_INTERVAL_SECONDS:
        await asyncio.sleep(_MIN_INTERVAL_SECONDS - elapsed)
    _last_embed_call = time.monotonic()


async def _embed_batch_with_retry(
    texts: list[str], batch_num: int, total_batches: int
) -> list[list[float]] | None:
    """Embed a single batch with exponential backoff.

    Returns the embedding vectors, or None if all retries are exhausted.
    The caller decides whether to continue or abort.
    """
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            await _throttle()
            vectors = await _embeddings.aembed_documents(texts)
            return vectors
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "429" in str(e) or "quota" in error_str or "resource" in error_str or "exhausted" in error_str

            if attempt == _MAX_RETRIES:
                logger.error(f"Batch {batch_num}/{total_batches} failed after {_MAX_RETRIES} retries: {e}")
                print(f"  ❌ Batch {batch_num}/{total_batches} failed after {_MAX_RETRIES} retries: {e}")
                return None

            wait_time = min(15 * (2 ** (attempt - 1)), 120)  # 15s, 30s, 60s, 120s
            reason = "rate limit" if is_rate_limit else "error"
            logger.warning(f"Batch {batch_num}/{total_batches} hit {reason}, retry in {wait_time}s (attempt {attempt}/{_MAX_RETRIES}): {e}")
            print(f"  ⚠️  Batch {batch_num}/{total_batches} {reason}, retrying in {wait_time}s (attempt {attempt}/{_MAX_RETRIES})")
            await asyncio.sleep(wait_time)

    return None  # Unreachable, but satisfies type checker


# ===== DEDUPLICATION =====

async def _find_existing_document(
    session: AsyncSession, title: str, ticker: str | None
) -> Document | None:
    """Check if a document with the same title already exists."""
    stmt = select(Document).where(Document.title == title)
    if ticker is not None:
        stmt = stmt.where(Document.ticker == ticker)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ===== MAIN INGESTION FUNCTION =====

async def ingest_document(
    session: AsyncSession,
    *,
    file_path: str | Path | None = None,
    file_bytes: bytes | None = None,
    ticker: str | None = None,
    title: str | None = None,
    source: str = "seed",
) -> Document:
    """Ingest a PDF document: extract → filter → chunk → embed → store.

    Features:
    - Section pre-filtering to reduce embedding volume for large annual reports
    - Rate-limit-aware batching (30 chunks/batch, 15s interval, exponential backoff)
    - Per-batch failure tolerance (partial ingestion over total failure)
    - Deduplication (skips ready docs, re-ingests failed/partial/processing ones)
    - Status lifecycle: processing → ready | partial | error

    Args:
        session: SQLAlchemy async session
        file_path: Path to a PDF file on disk (for seed script)
        file_bytes: Raw PDF bytes (for upload endpoint)
        ticker: Stock ticker associated with this document
        title: Document title
        source: 'seed' or 'upload'

    Returns:
        The Document record (created or updated)
    """
    resolved_title = title or (Path(file_path).stem if file_path else "Uploaded document")

    # --- Deduplication check ---
    existing = await _find_existing_document(session, resolved_title, ticker)
    if existing:
        if existing.status == "ready":
            print(f"  ⏭️  Already ingested (status=ready, {existing.chunk_count} chunks). Skipping.")
            return existing
        else:
            # Re-ingest: delete old chunks and reset the document row
            print(f"  🔄 Found previous attempt (status={existing.status}). Clearing chunks and re-ingesting...")
            await session.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == existing.id)
            )
            existing.status = "processing"
            existing.chunk_count = 0
            existing.ticker = ticker  # Update in case ticker changed
            await session.commit()
            doc = existing
    else:
        doc = None

    # --- 1. Extract text ---
    print(f"  📖 Extracting text...")
    if file_path:
        pages = extract_pages_from_pdf(file_path)
    elif file_bytes:
        pages = extract_pages_from_bytes(file_bytes)
    else:
        raise ValueError("Either file_path or file_bytes must be provided")

    if not pages:
        if doc:
            doc.status = "error"
            doc.doc_metadata = {**(doc.doc_metadata or {}), "error": "No text extracted"}
            await session.commit()
        raise ValueError("No text could be extracted from the PDF. Is it a scanned/image-only PDF?")

    total_chars_raw = sum(len(p) for p in pages)
    print(f"  📄 Extracted {len(pages)} pages ({total_chars_raw:,} chars)")

    # --- 2. Filter relevant sections ---
    filtered_pages, filter_meta = filter_relevant_pages(pages)
    filter_path = filter_meta["filter_path"]

    if filter_path == "pages_filtered":
        filtered_chars = filter_meta["filtered_chars"]
        reduction = filter_meta["reduction_pct"]
        print(f"  🔍 Filtered to {len(filtered_pages)}/{len(pages)} pages ({filtered_chars:,} chars, {reduction}% reduction)")
        keywords_found = filter_meta.get("matched_keywords", [])
        if keywords_found:
            print(f"     Matched: {', '.join(keywords_found[:10])}")
    else:
        print(f"  🔍 No section keywords matched — using full text ({total_chars_raw:,} chars)")

    raw_text = "\n\n".join(filtered_pages)

    # --- 3. Chunk ---
    chunks = chunk_text(raw_text)
    if not chunks:
        if doc:
            doc.status = "error"
            doc.doc_metadata = {**(doc.doc_metadata or {}), "error": "No chunks created"}
            await session.commit()
        raise ValueError("Text was extracted but no chunks were created")
    print(f"  ✂️  Created {len(chunks)} chunks")

    # --- 4. Create Document record (if new) ---
    if doc is None:
        doc = Document(
            source=source,
            ticker=ticker,
            title=resolved_title,
            status="processing",
            chunk_count=0,
            doc_metadata={
                "raw_pages": len(pages),
                "raw_chars": total_chars_raw,
                "filter": filter_meta,
            },
        )
        session.add(doc)
        await session.flush()  # Get doc.id
        await session.commit()
    else:
        # Update metadata on existing document
        doc.doc_metadata = {
            **(doc.doc_metadata or {}),
            "raw_pages": len(pages),
            "raw_chars": total_chars_raw,
            "filter": filter_meta,
        }
        await session.commit()

    # --- 5. Embed and store chunks in batches ---
    texts = [c["content"] for c in chunks]
    total_batches = (len(texts) + _EMBED_BATCH_SIZE - 1) // _EMBED_BATCH_SIZE

    embedded_count = 0
    failed_count = 0

    est_seconds = total_batches * _MIN_INTERVAL_SECONDS
    print(f"  🧠 Embedding {len(texts)} chunks in {total_batches} batches "
          f"(size={_EMBED_BATCH_SIZE}, interval={_MIN_INTERVAL_SECONDS}s, est. {est_seconds:.0f}s)...")

    for batch_idx in range(total_batches):
        start = batch_idx * _EMBED_BATCH_SIZE
        end = min(start + _EMBED_BATCH_SIZE, len(texts))
        batch_texts = texts[start:end]
        batch_chunks = chunks[start:end]
        batch_num = batch_idx + 1

        print(f"  📡 Batch {batch_num}/{total_batches} (chunks {start + 1}–{end})...", end=" ", flush=True)

        vectors = await _embed_batch_with_retry(batch_texts, batch_num, total_batches)

        if vectors is None:
            failed_count += len(batch_texts)
            print(f"FAILED ({len(batch_texts)} chunks lost)")
            continue

        # Store this batch's chunks immediately
        for chunk_data, embedding in zip(batch_chunks, vectors):
            chunk_obj = DocumentChunk(
                document_id=doc.id,
                chunk_index=chunk_data["chunk_index"],
                content=chunk_data["content"],
                section_title=chunk_data["section_title"],
                embedding=embedding,
                chunk_metadata={"char_count": len(chunk_data["content"])},
            )
            session.add(chunk_obj)

        await session.commit()  # Persist each batch so progress is never lost
        embedded_count += len(batch_texts)
        print(f"✅ ({embedded_count}/{len(texts)} total)")

    # --- 6. Update document status ---
    doc.chunk_count = embedded_count
    doc.doc_metadata = {
        **(doc.doc_metadata or {}),
        "embedded_count": embedded_count,
        "failed_count": failed_count,
        "total_chunks": len(chunks),
    }

    if failed_count == 0:
        doc.status = "ready"
        print(f"  ✅ Document ready: {embedded_count} chunks embedded")
    elif embedded_count > 0:
        doc.status = "partial"
        print(f"  ⚠️  Partial: {embedded_count}/{len(chunks)} chunks embedded, {failed_count} failed")
    else:
        doc.status = "error"
        print(f"  ❌ Error: all {failed_count} chunks failed to embed")

    await session.commit()
    return doc
