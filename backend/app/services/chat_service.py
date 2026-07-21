import json
import logging
import uuid

from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.thread import Message, Thread

logger = logging.getLogger(__name__)


def _extract_text(content) -> str:
    """Gemini 3.5+ can return content as a list of content blocks (with 'extras'/'signature'
    for thought preservation) instead of a plain string. Flatten to plain text for storage/SSE."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def create_thread(session: AsyncSession, title: str | None = None) -> Thread:
    thread = Thread(title=title)
    session.add(thread)
    await session.flush()
    await session.commit()
    return thread


async def _save_message(
    session: AsyncSession, thread_id: uuid.UUID, role: str, content: str | None,
    ui_blocks: list | None = None, tool_trace: list | None = None,
) -> Message:
    message = Message(thread_id=thread_id, role=role, content=content, ui_blocks=ui_blocks, tool_trace=tool_trace)
    session.add(message)
    await session.flush()
    return message


async def stream_chat_response(
    graph, session_maker: async_sessionmaker[AsyncSession], thread_id: uuid.UUID, user_content: str,
):
    """Opens its own DB session for the lifetime of the stream — deliberately not
    using FastAPI's Depends(get_db), which tears down before a StreamingResponse
    finishes sending."""
    async with session_maker() as session:
        await _save_message(session, thread_id, role="user", content=user_content)
        await session.commit()

        config = {"configurable": {"thread_id": str(thread_id)}}
        input_state = {"messages": [HumanMessage(content=user_content)]}

        final_text = ""
        final_ui_blocks: list[dict] = []
        final_trace: list[dict] = []

        # Send an immediate heartbeat so the client knows the stream is open
        yield _sse("status", {"stage": "planning"})
        logger.info("[stream] Started — sending planning status for thread %s", thread_id)

        try:
            async for event in graph.astream(input_state, config=config, stream_mode="updates"):
                for node_name, node_output in event.items():
                    logger.info("[stream] Node completed: %s", node_name)
                    if node_name == "planner":
                        # Planner finished — tools are next
                        yield _sse("status", {"stage": "executing"})
                    elif node_name == "tool_executor":
                        trace = node_output.get("tool_trace", [])
                        final_trace.extend(trace)
                        for entry in trace:
                            yield _sse("tool_call", entry)
                        # Tools done — responder is next
                        yield _sse("status", {"stage": "responding"})
                    elif node_name == "responder":
                        msg = node_output["messages"][0]
                        final_text = _extract_text(msg.content)
                        final_ui_blocks = node_output.get("ui_blocks", [])
                        yield _sse("token", {"text": final_text})
                        for block in final_ui_blocks:
                            yield _sse("ui_block", block)
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error("[stream] Error in graph execution: %s", e)
            yield _sse("error", {"message": str(e)})

        await _save_message(
            session, thread_id, role="assistant", content=final_text,
            ui_blocks=final_ui_blocks, tool_trace=final_trace,
        )
        await session.commit()
        logger.info("[stream] Done for thread %s", thread_id)
        yield _sse("done", {})