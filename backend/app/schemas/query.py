from pydantic import BaseModel


"""
{
  "technology": "python",
  "question": "My system currently uses 3.10. What are the breaking changes from 3.10 to 3.14.7?"
}
"""
class QueryRequest(BaseModel):
    technology: str
    question: str

"""
{
  "answer": "LLM generated respone for breaking changes from 3.10 to 3.14.7"
}
"""
class QueryResponse(BaseModel):
    answer: str    
