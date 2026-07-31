"""RAG search tool: embed the query → cosine similarity over document_chunks → return top-k with citations."""

from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_maker
from app.models.document import Document, DocumentChunk

_embeddings = HuggingFaceEndpointEmbeddings(
    huggingfacehub_api_token=settings.huggingface_api_key,
    model="BAAI/bge-base-en-v1.5",
)


from langchain_core.tools import InjectedToolArg
from typing import Annotated

@tool
async def rag_search(
    query: str, 
    ticker: str | None = None, 
    top_k: int = 3, 
    thread_id: Annotated[str, InjectedToolArg] = None
) -> dict:
    """Search documents available in this conversation for relevant information.
    
    If the user has uploaded a PDF in this thread, this searches THEIR document
    directly — no ticker or company name is required when the user refers to
    'the pdf', 'the document', 'the report', or similar, since it's scoped to
    this conversation automatically. Only pass a ticker if the user is asking
    about a specific seeded/demo company's filing instead of their own upload.

    Args:
        query: The search query describing what information to find
        ticker: Optional stock ticker to filter results (e.g. 'RELIANCE.NS')
        top_k: Number of results to return (default 3)
    """
    # 1. Embed the query
    query_embedding = await _embeddings.aembed_query(query)

    # 2. Build the SQL query with cosine similarity
    async with async_session_maker() as session:
        if ticker:
            result = await session.execute(
                text("""
                    SELECT
                        dc.content,
                        dc.section_title,
                        dc.chunk_index,
                        d.title AS document_title,
                        d.ticker,
                        d.source,
                        1 - (dc.embedding <=> CAST(:embedding AS vector)) AS similarity
                    FROM document_chunks dc
                    JOIN documents d ON dc.document_id = d.id
                    JOIN document_threads dt ON dt.document_id = d.id
                    WHERE d.ticker = :ticker
                      AND d.status IN ('ready', 'partial')
                      AND dt.thread_id = CAST(:thread_id AS UUID)
                    ORDER BY dc.embedding <=> CAST(:embedding AS vector)
                    LIMIT :top_k
                """),
                {
                    "embedding": str(query_embedding),
                    "ticker": ticker,
                    "top_k": top_k,
                    "thread_id": thread_id,
                },
            )
        else:
            result = await session.execute(
                text("""
                    SELECT
                        dc.content,
                        dc.section_title,
                        dc.chunk_index,
                        d.title AS document_title,
                        d.ticker,
                        d.source,
                        1 - (dc.embedding <=> CAST(:embedding AS vector)) AS similarity
                    FROM document_chunks dc
                    JOIN documents d ON dc.document_id = d.id
                    JOIN document_threads dt ON dt.document_id = d.id
                    WHERE d.status IN ('ready', 'partial')
                      AND dt.thread_id = CAST(:thread_id AS UUID)
                    ORDER BY dc.embedding <=> CAST(:embedding AS vector)
                    LIMIT :top_k
                """),
                {
                    "embedding": str(query_embedding),
                    "top_k": top_k,
                    "thread_id": thread_id,
                },
            )

        rows = result.fetchall()

    if not rows:
        return {"error": "No matching documents found. The document database may be empty — have you run the seed script?"}

    excerpts = []
    for row in rows:
        excerpts.append({
            "content": row.content,
            "section_title": row.section_title or "General",
            "document_title": row.document_title or "Unknown Document",
            "ticker": row.ticker,
            "source": row.source,
            "similarity": round(float(row.similarity), 4),
        })

    return {
        "query": query,
        "ticker_filter": ticker,
        "results": excerpts,
    }
