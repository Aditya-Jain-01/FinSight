from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.database import async_session_maker
from app.schemas.document import UploadDocumentResponse
from app.services.ingestion_service import ingest_document

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"application/pdf"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB


@router.post("/documents/upload", response_model=UploadDocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    ticker: str | None = Form(None),
    title: str | None = Form(None),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 50MB).")
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    resolved_title = title or file.filename.rsplit(".", 1)[0].replace("_", " ").title()

    async with async_session_maker() as session:
        try:
            document = await ingest_document(
                session=session,
                file_bytes=contents,
                ticker=ticker,
                title=resolved_title,
                source="upload",
            )
            # ingest_document commits internally per batch — no extra commit needed
        except Exception as e:
            # Note: partial progress (already-committed batches) is intentionally preserved.
            # The document will have status='error' or 'partial' and can be re-ingested.
            raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}") from e

    return UploadDocumentResponse(
        document_id=document.id,
        title=document.title,
        chunk_count=document.chunk_count,
    )
