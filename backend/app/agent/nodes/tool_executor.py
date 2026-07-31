import json
import time

from langchain_core.messages import ToolMessage

from app.agent.tools.registry import TOOLS_BY_NAME


async def tool_executor_node(state):
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None) or []

    tool_messages = []
    trace_entries = []

    for call in tool_calls:
        tool_fn = TOOLS_BY_NAME.get(call["name"])
        start = time.monotonic()
        error = None
        try:
            if tool_fn is None:
                raise ValueError(f"Unknown tool: {call['name']}")
            
            call_args = dict(call["args"])
            # Inject thread_id for tools that need it (like rag_search)
            if "thread_id" in tool_fn.args:
                call_args["thread_id"] = state.get("thread_id")
                
            raw_result = await tool_fn.ainvoke(call_args)
            if isinstance(raw_result, dict) and raw_result.get("error"):
                error = raw_result["error"]
        except Exception as e:  # noqa: BLE001 — tool failures shouldn't crash the graph
            raw_result = {"error": str(e)}
            error = str(e)
        latency_ms = round((time.monotonic() - start) * 1000)

        tool_messages.append(ToolMessage(content=json.dumps(raw_result), tool_call_id=call["id"]))
        trace_entries.append({
            "tool": call["name"],
            "args": call["args"],
            "latency_ms": latency_ms,
            "raw_result": raw_result,
            "error": error,
        })

    return {"messages": tool_messages, "tool_trace": trace_entries}