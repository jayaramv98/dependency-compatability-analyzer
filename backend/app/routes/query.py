from fastapi import APIRouter
from app.schemas.query import QueryRequest, QueryResponse

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    return QueryResponse(
        answer=f"Received query for {request.technology}: {request.question}"
    )