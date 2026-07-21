import uuid

from pydantic import BaseModel


class CreateThreadResponse(BaseModel):
    thread_id: uuid.UUID


class SendMessageRequest(BaseModel):
    content: str