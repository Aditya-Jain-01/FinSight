from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    tool_trace: list[dict]
    ui_blocks: list[dict]
    provider_meta: dict  # {"provider": str, "model": str, "fallback_used": bool}
    has_user_docs: bool
    thread_id: str | None
    skip_responder: bool  # Set by chat_service when streaming prose directly