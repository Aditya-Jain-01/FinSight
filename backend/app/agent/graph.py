from langgraph.graph import END, START, StateGraph

from app.agent.nodes.planner import planner_node
from app.agent.nodes.responder import responder_node
from app.agent.nodes.tool_executor import tool_executor_node
from app.agent.state import AgentState


def build_graph(checkpointer):
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("responder", responder_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "tool_executor")
    graph.add_edge("tool_executor", "responder")
    graph.add_edge("responder", END)

    return graph.compile(checkpointer=checkpointer)