import uuid

from pydantic import BaseModel


class UploadDocumentResponse(BaseModel):
    document_id: uuid.UUID
    title: str
    chunk_count: int
