from pydantic import BaseModel


"""
{
  "technology": "python",
  "question": "My system currently uses 3.10. What are the breaking changes from 3.10 to 3.14.7?"
}
"""
class QueryRequest(BaseModel):
    question: str = Field(
        description="The user query regarding dependency changes.",
        examples=["What are the spatial lookup GIS GDALRaster changes in Django 6.0.8?"]
    )

"""
{
  "answer": "LLM generated respone for breaking changes from 3.10 to 3.14.7"
}
"""
class QueryResponse(BaseModel):
    answer: str    
