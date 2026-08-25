# START -> Router -> Retrieval -> Reasoning -> Generation -> END

# app/agent/graph.py
from langgraph.graph import StateGraph, START, END
from app.agent.state import QueryState

# Import all your nodes' core logic (main functions)
from app.agent.nodes.router import route_query
from app.agent.nodes.retrieval import retrieve_documents
from app.agent.nodes.reasoning import evaluate_relevance
from app.agent.nodes.generation import generate_answer

def build_graph():
    """
    Constructs and compiles the main agentic RAG workflow.
    """
    print("--- BUILDING STATEGRAPH ORCHESTRATOR ---")
    
    # 1. Initialize the graph with your shared state schema
    workflow = StateGraph(QueryState)

    # 2. Register all the operational nodes
    workflow.add_node("router", route_query)
    workflow.add_node("retriever", retrieve_documents)
    workflow.add_node("reasoner", evaluate_relevance)
    workflow.add_node("generator", generate_answer)

    # 3. Wire the graph together using directed edges
    workflow.add_edge(START, "router")
    workflow.add_edge("router", "retriever")
    workflow.add_edge("retriever", "reasoner")
    workflow.add_edge("reasoner", "generator")
    workflow.add_edge("generator", END)

    # 4. Compile into an executable application
    compiled_app = workflow.compile()
    print("--- STATEGRAPH COMPILED SUCCESSFULLY ---\n")
    
    return compiled_app

# --- OPTIONAL: Quick test block to run the whole pipeline ---
if __name__ == "__main__":
    app = build_graph()
    
    # You only need to pass the entry data!
    initial_state = {
        "question": "What are the spatial lookup GIS GDALRaster changes in Django 6.0.8?"
    }
    
    print("\n==================================================")
    print("🚀 RUNNING END-TO-END RAG PIPELINE")
    print("==================================================\n")
    
    for output in app.stream(initial_state):
        for key, value in output.items():
            print(f"✅ Node '{key}' completed execution.")
            
    print("\n==================================================")
    print("FINAL AGENT ANSWER:")
    print("==================================================")
    
    if "generator" in output:
        print(output["generator"].get("answer", "No answer generated."))