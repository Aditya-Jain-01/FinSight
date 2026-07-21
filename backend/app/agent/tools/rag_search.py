"""RAG search tool: embed the query → cosine similarity over document_chunks → return top-k with citations."""

from langchain_core.tools import tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_maker
from app.models.document import Document, DocumentChunk

_embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=settings.google_api_key,
    output_dimensionality=768,
)


@tool
async def rag_search(query: str, ticker: str | None = None, top_k: int = 3) -> dict:
    """Search seeded financial documents (annual reports, filings) for information
    relevant to the query. Returns the top matching excerpts with citations.

    Use this tool when the user asks about information that would be in a company's
    annual report, filing, or other financial document — e.g. capex plans, revenue
    breakdown, management commentary, risk factors, strategic initiatives.

    Args:
        query: The search query describing what information to find
        ticker: Optional stock ticker to filter results (e.g. 'RELIANCE.NS')
        top_k: Number of results to return (default 3)
    """
    # 1. Embed the query
    query_embedding = await _embeddings.aembed_query(query)

    # 2. Build the SQL query with cosine similarity
    # Using raw SQL for the pgvector distance operator
    async with async_session_maker() as session:
        # Base query: join chunks with documents, compute cosine distance
        # NOTE: using CAST(:embedding AS vector) instead of :embedding::vector
        # because SQLAlchemy's text() interprets :: as a parameter delimiter
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
                    WHERE d.ticker = :ticker
                    ORDER BY dc.embedding <=> CAST(:embedding AS vector)
                    LIMIT :top_k
                """),
                {
                    "embedding": str(query_embedding),
                    "ticker": ticker,
                    "top_k": top_k,
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
                    ORDER BY dc.embedding <=> CAST(:embedding AS vector)
                    LIMIT :top_k
                """),
                {
                    "embedding": str(query_embedding),
                    "top_k": top_k,
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
