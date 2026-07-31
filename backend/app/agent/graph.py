from langgraph.graph import END, START, StateGraph

from app.agent.nodes.planner import planner_node
from app.agent.nodes.responder import responder_node
from app.agent.nodes.tool_executor import tool_executor_node
from app.agent.state import AgentState
from langchain_core.messages import AIMessage

def fallback_node(state: AgentState):
    msg = AIMessage(content="I wasn't able to generate a response to that — could you rephrase your question?")
    return {"messages": [msg]}

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    
    if getattr(last_message, "tool_calls", None):
        return "tool_executor"
    
    content = last_message.content
    has_text = False
    
    if isinstance(content, str) and content.strip():
        has_text = True
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text" and block.get("text", "").strip():
                has_text = True
            elif isinstance(block, str) and block.strip():
                has_text = True
                
    if has_text:
        return END
        
    return "fallback"

def build_graph(checkpointer):
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("responder", responder_node)
    graph.add_node("fallback", fallback_node)

    graph.add_edge(START, "planner")
    graph.add_conditional_edges("planner", should_continue)
    graph.add_edge("tool_executor", "responder")
    graph.add_edge("responder", END)
    graph.add_edge("fallback", END)

    return graph.compile(checkpointer=checkpointer)