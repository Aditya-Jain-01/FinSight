"""Ingestion service: PDF → text → chunks → embeddings → Postgres.

Shared function used by both the seed script and the upload endpoint.
Deliberately synchronous on the embedding calls — at MVP scale (5–8 PDFs,
~50–200 chunks each) this runs in under a minute and doesn't need a queue.
"""

import asyncio
import time
import uuid
from pathlib import Path

import pdfplumber
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, retry_if_exception_type, wait_exponential, stop_after_attempt

from app.config import settings
from app.models.document import Document, DocumentChunk

# Embedding model: 768-dim, matches the Vector(768) column in document_chunks
_embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=settings.google_api_key,
    output_dimensionality=768,
)

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=150,
    separators=["\n\n", "\n", ". ", " ", ""],
)

_EMBED_BATCH_SIZE = 100  # texts per API call
_MIN_INTERVAL_SECONDS = 2.0  # gap between batch calls, stay well under 100 req/min
_last_embed_call = 0.0


async def _throttle():
    global _last_embed_call
    elapsed = time.monotonic() - _last_embed_call
    if elapsed < _MIN_INTERVAL_SECONDS:
        await asyncio.sleep(_MIN_INTERVAL_SECONDS - elapsed)
    _last_embed_call = time.monotonic()


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=15, max=60),
    stop=stop_after_attempt(5),
)
async def _embed_batch(embeddings, texts: list[str]) -> list[list[float]]:
    await _throttle()
    return await embeddings.aembed_documents(texts)


async def embed_all_chunks(embeddings, chunk_texts: list[str]) -> list[list[float]]:
    """Embed all chunks for a document in batches, respecting free-tier rate limits."""
    all_vectors = []
    for i in range(0, len(chunk_texts), _EMBED_BATCH_SIZE):
        batch = chunk_texts[i : i + _EMBED_BATCH_SIZE]
        vectors = await _embed_batch(embeddings, batch)
        all_vectors.extend(vectors)
    return all_vectors


def extract_text_from_pdf(file_path: str | Path) -> str:
    """Extract all selectable text from a PDF using pdfplumber."""
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def extract_text_from_bytes(file_bytes: bytes) -> str:
    """Extract text from in-memory PDF bytes (for upload endpoint)."""
    import io
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


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


async def ingest_document(
    session: AsyncSession,
    *,
    file_path: str | Path | None = None,
    file_bytes: bytes | None = None,
    ticker: str | None = None,
    title: str | None = None,
    source: str = "seed",
) -> Document:
    """Ingest a PDF document: extract text, chunk, embed, store.

    Args:
        session: SQLAlchemy async session
        file_path: Path to a PDF file on disk (for seed script)
        file_bytes: Raw PDF bytes (for upload endpoint)
        ticker: Stock ticker associated with this document
        title: Document title (e.g. "Reliance Industries Annual Report 2024")
        source: 'seed' or 'upload'

    Returns:
        The created Document record
    """
    # 1. Extract text
    if file_path:
        raw_text = extract_text_from_pdf(file_path)
    elif file_bytes:
        raw_text = extract_text_from_bytes(file_bytes)
    else:
        raise ValueError("Either file_path or file_bytes must be provided")

    if not raw_text.strip():
        raise ValueError("No text could be extracted from the PDF. Is it a scanned/image-only PDF?")

    # 2. Chunk
    chunks = chunk_text(raw_text)
    if not chunks:
        raise ValueError("Text was extracted but no chunks were created")

    # 3. Embed all chunks in batches
    texts = [c["content"] for c in chunks]
    embeddings = await embed_all_chunks(_embeddings, texts)

    # 4. Create Document record
    doc = Document(
        source=source,
        ticker=ticker,
        title=title or (Path(file_path).stem if file_path else "Uploaded document"),
        chunk_count=len(chunks),
        doc_metadata={
            "char_count": len(raw_text),
            "chunk_count": len(chunks),
        },
    )
    session.add(doc)
    await session.flush()  # Get the doc.id

    # 5. Create DocumentChunk records
    for chunk_data, embedding in zip(chunks, embeddings):
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=chunk_data["chunk_index"],
            content=chunk_data["content"],
            section_title=chunk_data["section_title"],
            embedding=embedding,
            chunk_metadata={
                "char_count": len(chunk_data["content"]),
            },
        )
        session.add(chunk)

    await session.commit()
    return doc
