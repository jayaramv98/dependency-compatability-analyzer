from pydantic import BaseModel, Field


"""
{
  "question": "My system currently uses 3.10. What are the breaking changes from 3.10 to 3.14.7?"
}
"""
class QueryRequest(BaseModel):
    question: str = Field(
        description="The user query regarding dependency changes.",
        examples=["What are the spatial lookup GIS GDALRaster changes in Django 6.0.8?"]
    )

"""
The structured response generated from RAG pipeline & LLM
"""
class QueryResponse(BaseModel):
    summary: str
    breaking_changes: list[str] = []
    security_impact: list[str] = []
    developer_actions: list[str] = []
