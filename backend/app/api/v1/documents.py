import asyncio
import hashlib
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.database import async_session_maker
from app.models.document import Document, DocumentThread
from app.schemas.document import UploadDocumentResponse
from app.services.ingestion_service import ingest_document
from app.services.progress_bus import register_task, cleanup_task, publish

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_CONTENT_TYPES = {"application/pdf"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB

# Background tasks need to be referenced to prevent GC
_background_tasks: set[asyncio.Task] = set()


@router.post("/documents/upload", response_model=UploadDocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    thread_id: str | None = Form(None),
    ticker: str | None = Form(None),
    title: str | None = Form(None),
):
    # --- Validation (unchanged) ---
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 50MB).")
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    resolved_title = title or file.filename.rsplit(".", 1)[0].replace("_", " ").title()
    content_hash = hashlib.sha256(contents).hexdigest()

    # --- Create Document row immediately ---
    async with async_session_maker() as session:
        doc = Document(
            source="upload",
            ticker=ticker,
            title=resolved_title,
            content_hash=content_hash,
            status="processing",
            chunk_count=0,
        )
        session.add(doc)
        await session.flush()  # get doc.id
        if thread_id:
            session.add(DocumentThread(document_id=doc.id, thread_id=thread_id))
        await session.commit()
        doc_id = doc.id

    # --- Launch ingestion as background task ---
    async def _run_ingestion():
        async with async_session_maker() as session:
            try:
                # Re-fetch the document in the new session
                doc = await session.get(Document, doc_id)
                await ingest_document(
                    session=session,
                    file_bytes=contents,
                    thread_id=thread_id,
                    ticker=ticker,
                    title=resolved_title,
                    source="upload",
                    document=doc,
                )
            except asyncio.CancelledError:
                logger.info("Ingestion cancelled for doc %s", doc_id)
            except Exception:
                logger.exception("Background ingestion failed for doc %s", doc_id)
                # Ensure status is set to error
                try:
                    doc = await session.get(Document, doc_id)
                    if doc and doc.status == "processing":
                        doc.status = "error"
                        await session.commit()
                    await publish(doc_id, {
                        "phase": "complete", "status": "error",
                        "error": "Ingestion failed unexpectedly",
                    })
                except Exception:
                    logger.exception("Failed to set error status for doc %s", doc_id)
            finally:
                cleanup_task(doc_id)

    task = asyncio.create_task(_run_ingestion())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    register_task(doc_id, task)

    # --- Return immediately ---
    return UploadDocumentResponse(
        document_id=doc_id,
        title=resolved_title,
        chunk_count=0,  # Will be updated by the background task
    )
