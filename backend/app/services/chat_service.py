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

        from sqlalchemy import select, func
        from app.models.document import Document, DocumentThread
        # Determine if the thread has user-uploaded documents
        has_user_docs_count = await session.scalar(
            select(func.count()).select_from(DocumentThread).join(Document).where(
                DocumentThread.thread_id == thread_id,
                Document.source != "seed",
                Document.status == "ready"
            )
        )
        has_user_docs = (has_user_docs_count or 0) > 0

        config = {"configurable": {"thread_id": str(thread_id)}}
        input_state = {
            "messages": [HumanMessage(content=user_content)],
            "has_user_docs": has_user_docs,
            "thread_id": str(thread_id),
        }

        final_text = ""
        final_ui_blocks: list[dict] = []
        final_trace: list[dict] = []
        final_provider_meta: dict = {}
        used_streaming_responder = False

        # Send an immediate heartbeat so the client knows the stream is open
        yield _sse("status", {"stage": "planning"})
        logger.info("[stream] Started — sending planning status for thread %s", thread_id)

        try:
            async for event in graph.astream(input_state, config=config, stream_mode="updates"):
                for node_name, node_output in event.items():
                    logger.info("[stream] Node completed: %s", node_name)
                    if node_name == "planner":
                        msg = node_output["messages"][-1]
                        if not getattr(msg, "tool_calls", None):
                            # Short-circuit: answered directly by planner without tools
                            final_text = _extract_text(msg.content)
                            final_trace.append({
                                "tool": "_planner_direct",
                                "raw_result": "Answered directly by planner.",
                                "latency_ms": 0,
                                "args": {}
                            })
                            yield _sse("token", {"text": final_text})
                            yield _sse("status", {"stage": "responding"})
                        else:
                            # Planner finished — tools are next
                            yield _sse("status", {"stage": "executing"})

                    elif node_name == "tool_executor":
                        trace = node_output.get("tool_trace", [])
                        final_trace.extend(trace)
                        for entry in trace:
                            yield _sse("tool_call", entry)

                        # --- Phase 2: emit UI blocks immediately after tool_executor ---
                        from app.agent.nodes.responder import build_ui_blocks_from_trace, stream_responder_prose
                        final_ui_blocks = build_ui_blocks_from_trace(final_trace)
                        for block in final_ui_blocks:
                            yield _sse("ui_block", block)

                        yield _sse("status", {"stage": "responding"})

                        # --- Phase 2: stream prose token-by-token ---
                        # Get the current messages from the graph state for the responder
                        # We need the full message history including tool results
                        graph_state = await graph.aget_state(config)
                        current_messages = graph_state.values.get("messages", [])

                        accumulated_text = ""
                        async for token_chunk in stream_responder_prose(current_messages):
                            accumulated_text += token_chunk
                            yield _sse("token_delta", {"text": token_chunk})

                        final_text = accumulated_text
                        yield _sse("token_done", {"text": final_text})

                        # Fallback for empty bubble regression
                        if not final_text.strip() and final_ui_blocks:
                            final_text = "Here are the relevant documents I found:"
                            yield _sse("token_done", {"text": final_text})

                        used_streaming_responder = True
                        # Get provider meta from the graph state
                        final_provider_meta = graph_state.values.get("provider_meta", {})

                        # CRITICAL: Tell the responder_node to skip its LLM call and
                        # ui_block construction.  Without this the graph continues to
                        # execute responder_node (tool_executor → responder edge),
                        # which would rebuild & re-emit the same ui_blocks a second
                        # time — the root cause of the duplicate PriceChart/MetricCard bug.
                        await graph.aupdate_state(config, {
                            "skip_responder": True,
                        })

                        # Break the inner `for node_name …` loop. The outer
                        # `async for event in graph.astream(…)` will still deliver
                        # the responder node's (now-empty) output, but the elif
                        # branch below will see used_streaming_responder and skip it.
                        break

                    elif node_name == "responder" or node_name == "fallback":
                        # If we already streamed prose + UI blocks from the
                        # tool_executor branch, skip — this node's output is
                        # the (now-empty) result of responder_node after
                        # skip_responder was set.
                        if used_streaming_responder:
                            continue

                        # This path only fires if the streaming responder was
                        # somehow bypassed (e.g. graph structure change).
                        msg = node_output["messages"][-1]
                        final_text = _extract_text(msg.content)
                        final_ui_blocks = node_output.get("ui_blocks", [])
                        final_provider_meta = node_output.get("provider_meta", {})

                        # Fallback for empty bubble regression
                        if not final_text.strip() and final_ui_blocks:
                            final_text = "Here are the relevant documents I found:"

                        yield _sse("token", {"text": final_text})
                        for block in final_ui_blocks:
                            yield _sse("ui_block", block)

            # Update the graph state with the assistant's response if we streamed it ourselves
            # (Done outside the async for loop to prevent lock contention in PostgresSaver)
            if used_streaming_responder and final_text:
                from langchain_core.messages import AIMessage
                await graph.aupdate_state(config, {
                    "messages": [AIMessage(content=final_text)],
                    "ui_blocks": final_ui_blocks,
                    "provider_meta": final_provider_meta
                })

        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error("[stream] Error in graph execution: %s", e)
            yield _sse("error", {"message": str(e)})

        if final_provider_meta:
            final_trace.append({
                "tool": "_llm_provider",
                "raw_result": final_provider_meta
            })

        await _save_message(
            session, thread_id, role="assistant", content=final_text,
            ui_blocks=final_ui_blocks, tool_trace=final_trace,
        )
        await session.commit()
        logger.info("[stream] Done for thread %s (provider: %s, fallback: %s)",
                    thread_id,
                    final_provider_meta.get("provider", "unknown"),
                    final_provider_meta.get("fallback_used", False))
        yield _sse("done", {"provider_meta": final_provider_meta})