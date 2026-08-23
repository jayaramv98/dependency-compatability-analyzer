from app.agent.state import QueryState
from app.services.embed_store import ChromaReader
from app.services.cohere_client import embed_query

## We will put the User Query embedding & Vector DB retrieval logic here
## Uses Cohere Embed service to embed query
## Uses dynamic operator mapping (LLM generated) for version in Chroma DB collection
## Applies Semantic similarity search + metadata filtering to retrieve relevant top 10 chunks

def retrieve_documents(state: QueryState) -> dict:
    """
    Reads the extracted search parameters from the state, dynamically builds 
    the ChromaDB metadata filters, and retrieves the top matching chunks.
    """
    print("--- RETRIEVAL NODE: Fetching from ChromaDB ---")
    
    search_query = state["search_query"]
    technology = state.get("technology", "django")
    
    # Single versions
    v_major = state.get("version_major")
    v_minor = state.get("version_minor")
    v_patch = state.get("version_patch")
    operator = state.get("version_operator", "==")
    
    # Range versions
    curr_major = state.get("current_version_major")
    target_major = state.get("target_version_major")
    
    is_breaking = state.get("is_breaking")
    
    # 1. Map the LLM string operator to ChromaDB's syntax
    op_map = {
        "==": "$eq",
        ">=": "$gte",
        "<=": "$lte",
        ">": "$gt",
        "<": "$lt"
    }
    chroma_op = op_map.get(operator, "$eq")
    
    # 2. Build the dynamic metadata filter clause
    where_conditions = [{"technology": {"$eq": technology}}]
    
    if v_major is not None:
        where_conditions.append({"version_major": {chroma_op: v_major}})
    if v_minor is not None:
        where_conditions.append({"version_minor": {chroma_op: v_minor}})
    if v_patch is not None:
        where_conditions.append({"version_patch": {chroma_op: v_patch}})
        
    # Handle range filters (if upgrading)
    if curr_major is not None and target_major is not None:
        where_conditions.append({"version_major": {"$gte": curr_major}})
        where_conditions.append({"version_major": {"$lte": target_major}})
        
    if is_breaking is True:
        where_conditions.append({"is_breaking": {"$eq": True}})
        
    # Chroma requires the "$and" operator if there are multiple conditions
    if len(where_conditions) > 1:
        where_clause = {"$and": where_conditions}
    else:
        where_clause = where_conditions[0]
    
    print(f" > Applied Filters: {where_clause}")
    
    # 3. Embed the query and retrieve matching chunks
    query_vector = embed_query(search_query)
    
    reader = ChromaReader(collection_name="django_release_notes")
    retrieved_chunks = reader.query_as_chunks(
        query_vector=query_vector,
        top_k_results=10,
        where=where_clause
    )
    
    print(f" > Retrieved {len(retrieved_chunks)} chunks from ChromaDB.\n")
    
    return {"retrieved_chunks": retrieved_chunks}

if __name__ == "__main__":
    # Test with the output state from the router
    test_state: QueryState = {
        "question": "What are the breaking changes in Django 6.0.8?",
        "search_query": "summary of changes and updates",
        "technology": "django",
        "version_major": 6,
        "version_minor": 0,
        "version_patch": 8,
        "version_operator": "==",
        "current_version_major": None,
        "current_version_minor": None,
        "target_version_major": None,
        "target_version_minor": None,
        "is_breaking": True,
        "retrieved_chunks": [],
        "answer": ""
    }
    
    output = retrieve_documents(test_state)
    for i, chunk in enumerate(output["retrieved_chunks"], 1):
        print(f"[{i}] {chunk.metadata.section_title} (v{chunk.metadata.version}): {chunk.text[:120]}...")