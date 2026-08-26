from fastapi import APIRouter, HTTPException
from app.schemas.query import QueryRequest, QueryResponse
from app.agent.graph import build_graph

router = APIRouter()

# Initializes the langgraph state graph on route initialization
agent_executor = build_graph()

@router.post("/query", response_model=QueryResponse)
async def invokeAgent(payload: QueryRequest):
    """
    Processes a user query by invoking the LangGraph agent workflow.

    Args:
        payload: QueryRequest object containing the user's question

    Returns:
        QueryResponse with the agent's answer and analysis

    Raises:
        HTTPException: If the agent workflow is not initialized or execution fails
    """
    
    if not agent_executor:
        raise HTTPException(status_code=503, detail="Agent workflow is not initialized.")

    try:
        # 1. Initialize input state
        initial_state = {"question": payload.question}

        # 2. Invoke the compiled LangGraph workflow (async)
        final_state = await agent_executor.ainvoke(initial_state)

        return QueryResponse(
            summary=final_state.get("summary", "No analysis could be generated."),
            breaking_changes=final_state.get("breaking_changes", []),
            security_impact=final_state.get("security_impact", []),
            developer_actions=final_state.get("developer_actions", [])
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")