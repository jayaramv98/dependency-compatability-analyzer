from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from app.agent.state import QueryState

# --- 1. Structured Output Schema ---
class RelevanceGrade(BaseModel):
    """Structured relevance evaluation returned by the reasoning LLM."""
    score: Literal["yes", "no"] = Field(
        description="Binary score: 'yes' if the chunks contain the answer, 'no' if they are irrelevant or lack the necessary facts."
    )
    explanation: str = Field(
        description="A 1-2 sentence technical justification for why the context is or is not sufficient."
    )

# --- 2. Prompt Template ---
GRADER_SYSTEM_PROMPT = """You are a strict technical relevance grader.
Your task is to evaluate if the retrieved documentation chunks contain sufficient factual information to answer the user's question.

CRITERIA:
- Grade 'yes' if at least one chunk directly discusses the specific feature, bug, or upgrade path the user asked about.
- Grade 'no' if the chunks are completely generic, unrelated, or do not contain the actual answer.
- You are strictly grading relevance. Do NOT answer the user's question.

User Question: {question}

Retrieved Context:
{context}
"""

grader_prompt = ChatPromptTemplate.from_messages([
    ("system", GRADER_SYSTEM_PROMPT),
    ("human", "Evaluate the relevance of the retrieved context.")
])

# --- 3. Gemini LLM Initialization ---
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0
)

structured_grader = llm.with_structured_output(RelevanceGrade)
grader_chain = grader_prompt | structured_grader

# --- 4. Node Function ---
def evaluate_relevance(state: QueryState) -> dict:
    """
    Evaluates retrieved chunks against the user question.
    Updates the state with whether the context is valid.
    """
    print("--- REASONING NODE: Evaluating Chunk Relevance ---")
    
    question = state["question"]
    chunks = state.get("retrieved_chunks", [])
    
    if not chunks:
        print(" > No chunks found in state. Grade: 'no'\n")
        return {"is_relevant": False}

    # Format chunk text into a single context string
    formatted_context = "\n\n---\n\n".join(
        f"[Source: {chunk.metadata.get('section_title', 'Unknown')} (v{chunk.metadata.get('version', 'Unknown')})]\n{chunk.text}"
        for chunk in chunks
    )
    
    result: RelevanceGrade = grader_chain.invoke({
        "question": question,
        "context": formatted_context
    })
    
    is_relevant = (result.score.lower() == "yes")
    
    print(f" > Grade: {result.score.upper()}")
    print(f" > Explanation: {result.explanation}\n")
    
    return {"is_relevant": is_relevant}