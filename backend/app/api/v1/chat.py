import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker, get_db
from app.schemas.chat import CreateThreadResponse, SendMessageRequest
from app.services.chat_service import create_thread, stream_chat_response

router = APIRouter()


@router.post("/threads", response_model=CreateThreadResponse)
async def create_thread_route(db: AsyncSession = Depends(get_db)):
    thread = await create_thread(db)
    return CreateThreadResponse(thread_id=thread.id)


@router.post("/threads/{thread_id}/messages")
async def send_message(thread_id: uuid.UUID, body: SendMessageRequest, request: Request):
    graph = request.app.state.graph
    return StreamingResponse(
        stream_chat_response(graph, async_session_maker, thread_id, body.content),
        media_type="text/event-stream",
    )