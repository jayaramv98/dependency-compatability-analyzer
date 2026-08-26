# Builds ChromaDB filter and fetches vector chunks.
from typing import Any, Dict, List
from app.agent.state import QueryState
from app.services.embed_store import ChromaReader
from app.services.cohere_client import embed_query

from app.config import settings

## We will put the User Query embedding & Vector DB retrieval logic here
## Uses Cohere Embed service to embed query
## Uses dynamic operator mapping (LLM generated) for version in Chroma DB collection
## Applies Semantic similarity search + metadata filtering to retrieve relevant top 5 chunks

def build_chroma_filter(state: QueryState) -> Dict[str, Any]:
    """
    Builds mutually exclusive ChromaDB metadata filter conditions 
    for either a single target version or a multi-version upgrade range.
    """
    technology = state.get("technology", "django")
    where_conditions: List[Dict[str, Any]] = [{"technology": {"$eq": technology}}]

    # Breaking change filter
    if state.get("is_breaking") is True:
        where_conditions.append({"is_breaking": {"$eq": True}})

    # Range variables
    curr_major = state.get("current_version_major")
    curr_minor = state.get("current_version_minor")
    curr_patch = state.get("current_version_patch")
    target_major = state.get("target_version_major")
    target_minor = state.get("target_version_minor")
    target_patch = state.get("target_version_patch")

    is_range_query = curr_major is not None or target_major is not None

    # ==========================================
    # BRANCH A: RANGE / UPGRADE QUERY
    # ==========================================
    if is_range_query:
        # 1. Same major version (e.g., 6.0.1 to 6.0.8 or 6.0 to 6.2)
        if curr_major is not None and target_major is not None and curr_major == target_major:
            where_conditions.append({"version_major": {"$eq": curr_major}})
            
            # Minor version boundaries
            if curr_minor is not None and target_minor is not None:
                if curr_minor == target_minor:
                    where_conditions.append({"version_minor": {"$eq": curr_minor}})
                    # Patch version boundaries within the same minor release
                    if curr_patch is not None:
                        where_conditions.append({"version_patch": {"$gte": curr_patch}})
                    if target_patch is not None:
                        where_conditions.append({"version_patch": {"$lte": target_patch}})
                else:
                    where_conditions.append({"version_minor": {"$gte": curr_minor}})
                    where_conditions.append({"version_minor": {"$lte": target_minor}})
            elif curr_minor is not None:
                where_conditions.append({"version_minor": {"$gte": curr_minor}})
            elif target_minor is not None:
                where_conditions.append({"version_minor": {"$lte": target_minor}})

        # 2. Cross major versions (e.g., 4.2 to 6.0)
        # Split into 3 chunks (filters)
        else:
            or_conditions = []
            
            # For current major version filter
            # Start Major Boundary (e.g., major == 4 AND minor >= 2)
            start_boundary = [{"version_major": {"$eq": curr_major}}]
            if curr_minor is not None:
                start_boundary.append({"version_minor": {"$gte": curr_minor}})
            or_conditions.append({"$and": start_boundary} if len(start_boundary) > 1 else start_boundary[0])
            
            # If there is whole major release in between (get everything from these)
            # Intermediate Majors (e.g., major > 4 AND major < 6)
            if target_major - curr_major > 1:
                or_conditions.append({
                    "$and": [
                        {"version_major": {"$gt": curr_major}},
                        {"version_major": {"$lt": target_major}}
                    ]
                })
                
            # For target major version filter    
            # Target Major Boundary (e.g., major == 6 AND minor <= 0)
            end_boundary = [{"version_major": {"$eq": target_major}}]
            if target_minor is not None:
                end_boundary.append({"version_minor": {"$lte": target_minor}})
            or_conditions.append({"$and": end_boundary} if len(end_boundary) > 1 else end_boundary[0])
            
            # Append the OR block to the main conditions
            where_conditions.append({"$or": or_conditions})

    # ==========================================
    # BRANCH B: SINGLE VERSION QUERY
    # ==========================================
    else:
        v_major = state.get("version_major")
        v_minor = state.get("version_minor")
        v_patch = state.get("version_patch")
        operator = state.get("version_operator", "==")

        op_map = {
            "==": "$eq",
            ">=": "$gte",
            "<=": "$lte",
            ">": "$gt",
            "<": "$lt"
        }
        chroma_op = op_map.get(operator, "$eq")

        if v_major is not None:
            where_conditions.append({"version_major": {chroma_op: v_major}})
        if v_minor is not None:
            where_conditions.append({"version_minor": {chroma_op: v_minor}})
        if v_patch is not None:
            where_conditions.append({"version_patch": {chroma_op: v_patch}})

    # Wrap in $and if multiple conditions exist
    if len(where_conditions) > 1:
        return {"$and": where_conditions}
    return where_conditions[0]


def retrieve_documents(state: QueryState) -> dict:
    """
    Reads search parameters from state, generates the Chroma filter, 
    and retrieves matching vector chunks.
    """
    print("--- RETRIEVAL NODE: Fetching from ChromaDB ---")
    
    search_query = state["search_query"]
    where_clause = build_chroma_filter(state)
    
    print(f" > Query: '{search_query}'")
    print(f" > Applied Filters: {where_clause}")
    
    query_vector = embed_query(search_query)
    
    reader = ChromaReader(settings.django_chroma_collection)
    retrieved_chunks, distances = reader.query_as_chunks(
        query_vector=query_vector,  
        top_k_results=5,
        where=where_clause
    )
    
    print(f" > Retrieved {len(retrieved_chunks)} chunks from ChromaDB.\n")
    return {
        "retrieved_chunks": retrieved_chunks,
        "distances": distances
    }



#### TEST SCRIPTS code
import json

def test_filter_construction():
    """Unit tests for metadata filter generation across various query types."""
    print("==================================================")
    print("RUNNING UNIT TESTS: Filter Construction Logic")
    print("==================================================")

    # Case 1: Single specific version with breaking change
    state_single: QueryState = {
        "question": "What are breaking changes in Django 6.0.8?",
        "search_query": "summary of changes and updates",
        "technology": "django",
        "version_major": 6,
        "version_minor": 0,
        "version_patch": 8,
        "version_operator": "==",
        "current_version_major": None,
        "current_version_minor": None,
        "current_version_patch": None,
        "target_version_major": None,
        "target_version_minor": None,
        "target_version_patch": None,
        "is_breaking": True,
        "retrieved_chunks": [],
        "answer": ""
    }
    filter_1 = build_chroma_filter(state_single)
    print("\n[Test 1] Single Version (6.0.8, is_breaking=True):")
    print(json.dumps(filter_1, indent=2))
    assert "$and" in filter_1
    assert {"version_patch": {"$eq": 8}} in filter_1["$and"]
    assert {"is_breaking": {"$eq": True}} in filter_1["$and"]

    # Case 2: Comparison operator (since Django 4.2)
    state_operator: QueryState = {
        "question": "What changed since Django 4.2?",
        "search_query": "summary of changes and updates",
        "technology": "django",
        "version_major": 4,
        "version_minor": 2,
        "version_patch": None,
        "version_operator": ">=",
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
    filter_2 = build_chroma_filter(state_operator)
    print("\n[Test 2] Operator Filter (>= 4.2):")
    print(json.dumps(filter_2, indent=2))
    assert {"version_major": {"$gte": 4}} in filter_2["$and"]
    assert {"version_minor": {"$gte": 2}} in filter_2["$and"]

    # Case 3: Patch-level upgrade range within same minor version (6.0.1 to 6.0.8)
    state_patch_range: QueryState = {
        "question": "What broke from Django 6.0.1 to 6.0.8?",
        "search_query": "summary of changes and updates",
        "technology": "django",
        "version_major": None,
        "version_minor": None,
        "version_patch": None,
        "version_operator": "==",
        "current_version_major": 6,
        "current_version_minor": 0,
        "current_version_patch": 1,
        "target_version_major": 6,
        "target_version_minor": 0,
        "target_version_patch": 8,
        "is_breaking": True,
        "retrieved_chunks": [],
        "answer": ""
    }
    filter_3 = build_chroma_filter(state_patch_range)
    print("\n[Test 3] Patch Range (6.0.1 -> 6.0.8):")
    print(json.dumps(filter_3, indent=2))
    assert {"version_major": {"$eq": 6}} in filter_3["$and"]
    assert {"version_minor": {"$eq": 0}} in filter_3["$and"]
    assert {"version_patch": {"$gte": 1}} in filter_3["$and"]
    assert {"version_patch": {"$lte": 8}} in filter_3["$and"]

    # Case 4: Cross-major upgrade range (4.2 to 6.0)
    state_cross_major: QueryState = {
        "question": "What broke from Django 4.2 to 6.0?",
        "search_query": "summary of changes and updates",
        "technology": "django",
        "version_major": None,
        "version_minor": None,
        "version_patch": None,
        "version_operator": "==",
        "current_version_major": 4,
        "current_version_minor": 2,
        "current_version_patch": None,
        "target_version_major": 6,
        "target_version_minor": 0,
        "target_version_patch": None,
        "is_breaking": True,
        "retrieved_chunks": [],
        "answer": ""
    }
    filter_4 = build_chroma_filter(state_cross_major)
    print("\n[Test 4] Cross-Major Range (4.2 -> 6.0):")
    print(json.dumps(filter_4, indent=2))
    
    # --- UPDATED ASSERTIONS ---
    assert {"technology": {"$eq": "django"}} in filter_4["$and"]
    assert {"is_breaking": {"$eq": True}} in filter_4["$and"]
    
    # Verify the $or block was generated for the cross-major logic
    has_or_clause = any("$or" in condition for condition in filter_4["$and"])
    assert has_or_clause, "Cross-major filter should use an $or clause"

    print("\n[PASS] All filter construction tests passed successfully!\n")


def test_live_retrieval_execution():
    """Integration test executing ChromaDB retrieval against live indexed vectors."""
    print("==================================================")
    print("RUNNING INTEGRATION TEST: ChromaDB Live Retrieval")
    print("==================================================")

    test_state: QueryState = {
        "question": "What are spatial lookup changes in Django 6.0.8?",
        "search_query": "spatial lookup GIS GDALRaster",
        "technology": "django",
        "version_major": 6,
        "version_minor": 0,
        "version_patch": 8,
        "version_operator": "==",
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

    result = retrieve_documents(test_state)
    chunks = result.get("retrieved_chunks", [])
    distance = result.get("distances")

    print(f"Retrieved Chunks Count: {len(chunks)}")
    for idx, chunk in enumerate(chunks, 1):
        # Use getattr() safely instead of dict .get()
        section = getattr(chunk.metadata, 'section_title', 'N/A')
        version = getattr(chunk.metadata, 'version', 'N/A')
        
        print(f"\n--- Chunk [{idx}] ---")
        print(f"Section: {section}")
        print(f"Version: {version}")
        print(f"Snippet: {chunk.text}...")
        print(f"Distance/Score: {distance[idx - 1]}")

    print("\n[PASS] Retrieval execution completed without errors!\n")


##### Run "python -m app.agent.nodes.retrieval"
if __name__ == "__main__":
    test_filter_construction()
    test_live_retrieval_execution()