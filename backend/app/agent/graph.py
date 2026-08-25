# START -> Router -> Retrieval -> Reasoning -> Generation -> END

# app/agent/graph.py
from langgraph.graph import StateGraph, START, END
from app.agent.state import QueryState

# Import all your hard work!
from app.agent.nodes.router import extract_metadata
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
    workflow.add_node("router", extract_metadata)
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
    
    # The only thing you need to provide is the initial question!
    initial_state = {
        "question": "What are the spatial lookup GIS GDALRaster changes in Django 6.0.8?",
        "search_query": "",
        "technology": "",
        "version_major": None,
        "version_minor": None,
        "version_patch": None,
        "version_operator": None,
        "current_version_major": None,
        "current_version_minor": None,
        "current_version_patch": None,
        "target_version_major": None,
        "target_version_minor": None,
        "target_version_patch": None,
        "is_breaking": None,
        "retrieved_chunks": [],
        "answer": ""
    }
    
    print("\n==================================================")
    print("🚀 RUNNING END-TO-END RAG PIPELINE")
    print("==================================================\n")
    
    # Run the graph and stream the state updates
    for output in app.stream(initial_state):
        # LangGraph returns a dictionary where the key is the node that just finished
        for key, value in output.items():
            print(f"✅ Node '{key}' completed execution.")
            
    # Fetch the final answer from the state
    print("\n==================================================")
    print("FINAL AGENT ANSWER:")
    print("==================================================")
    final_state = app.get_state(app.config) # Note: LangGraph v0.1+ streams the final state at the end, but this is a safe fallback print
    
    # If the stream yielded the final output dict directly, we can grab it from there
    # For simplicity, if we just want to see the last chunk:
    if "generator" in output:
        print(output["generator"].get("answer", "No answer generated."))