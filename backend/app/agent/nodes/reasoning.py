# Evaluates whether chunks factually satisfy the question (is_relevant: bool).
from typing import Literal
from pydantic import BaseModel, Field

from app.config import settings

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agent.state import QueryState

# --- 1. Structured Output Schema ---
class RelevanceResult(BaseModel):
    relevant_chunk_ids: list[int] = Field(
        default_factory=list,
        description="List of integer IDs for chunks that directly provide information to answer the question."
    )
    reasoning: str = Field(
        description="Brief explanation of why these chunks were selected or rejected."
    )

# --- 2. Prompt & Model Setup ---
REASONING_PROMPT = """You are a technical document relevance grader.
Review the user question and the retrieved documentation chunks.
Identify which chunks contain relevant technical information to answer the question.

Question: {question}

Retrieved Chunks:
{context}
"""

grader_prompt = ChatPromptTemplate.from_messages([
    ("system", REASONING_PROMPT),
    ("human", "Evaluate the relevance of the retrieved context.")
])

# --- 3. Gemini LLM Initialization ---
llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    api_key=settings.gemini_api_key,
    temperature=0
)
# gemini-3.5-flash-lite
# gemini-3.1-pro-preview

structured_grader = llm.with_structured_output(RelevanceResult)
grader_chain = grader_prompt | structured_grader

# --- 4. Node Function ---
def evaluate_relevance(state: QueryState) -> dict:
    print("--- REASONING NODE: Evaluating Chunk Relevance ---")
    question = state["question"]
    chunks = state.get("retrieved_chunks", [])
    
    if not chunks:
        print(" > No chunks provided to grade.")
        return {"retrieved_chunks": []}
    
    # Send full text with ID labels
    formatted_context = "\n\n---\n\n".join(
        f"--- CHUNK ID: {idx} ---\n"
        f"Section: {getattr(chunk.metadata, 'section_title', 'Unknown')} (v{getattr(chunk.metadata, 'version', 'Unknown')})\n\n"
        f"{chunk.text}"
        for idx, chunk in enumerate(chunks, 1)
    )
    
    result: RelevanceResult = grader_chain.invoke({
        "question": question,
        "context": formatted_context
    })
    
    # Map 1-indexed IDs back to chunk array
    selected_indices = [cid - 1 for cid in result.relevant_chunk_ids if 1 <= cid <= len(chunks)]
    retained_chunks = [chunks[i] for i in selected_indices]
    
    print(f" > Selected Chunks: {result.relevant_chunk_ids}")
    print(f" > Reasoning: {result.reasoning}")
    print(f" > Retained {len(retained_chunks)} of {len(chunks)} chunks.\n")
    
    return {"retrieved_chunks": retained_chunks}

### TEST SCRIPT
### Run "python -m app.agent.nodes.reasoning"

if __name__ == "__main__":
    from app.services.embed_store import Chunk, ChunkMetadata

    def test_reasoning_filtering():
        print("==================================================")
        print("RUNNING UNIT TEST: Reasoning Node Filtering")
        print("==================================================")

        # Helper to quickly construct complete ChunkMetadata mocks
        def make_meta(section: str, is_breaking: bool = False) -> ChunkMetadata:
            return ChunkMetadata(
                technology="django",
                version="6.0.8",
                version_major=6,
                version_minor=0,
                version_patch=8,
                release_date="2026-03-01",
                is_breaking=is_breaking,
                section_title=section,
                url="https://docs.djangoproject.com/en/6.0/releases/6.0.8/"
            )

        # 1. Mock the 5 chunks matching the Pydantic schema
        chunk_1 = Chunk(
            text="Spatial lookups allowed str and dict lookup values to be passed to class - django.contrib.gis.gdal.GDALRaster...",
            metadata=make_meta("CVE-2026-15307: Server-side file-write", is_breaking=True)
        )
        chunk_2 = Chunk(
            text="class - django.contrib.gis.geos.GEOSGeometry was subject to a potential denial-of-service attack when provided deeply nested GEOMETRYCOLLECTION...",
            metadata=make_meta("CVE-2026-15830: Potential DoS via nested geometry")
        )
        chunk_3 = Chunk(
            text="func - django.utils.translation.check_for_language was subject to a potential denial-of-service attack when checking many distinct, very long language codes...",
            metadata=make_meta("CVE-2026-15337: Potential DoS in check_for_language()")
        )
        chunk_4 = Chunk(
            text="Added compatibility for sqlparse 0.5.5 (ticket - 37235).",
            metadata=make_meta("Bugfixes")
        )
        chunk_5 = Chunk(
            text="The admin renders class - django.db.models.URLField values as clickable links on changelist views and read-only fields...",
            metadata=make_meta("CVE-2026-15920: Potential XSS via URLField")
        )

        # 2. Setup the query state
        test_state = {
            "question": "What are the spatial lookup GIS GDALRaster changes in Django 6.0.8?",
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
            "retrieved_chunks": [chunk_1, chunk_2, chunk_3, chunk_4, chunk_5], 
            "answer": ""
        }

        print(f"Initial Chunks to Grade: {len(test_state['retrieved_chunks'])}")
        print("Sending to Gemini for Relevance Grading...\n")

        # 3. Run the reasoning node
        updated_state = evaluate_relevance(test_state)
        filtered_chunks = updated_state.get("retrieved_chunks", [])

        # 4. Print filtered results
        print(f"\nRemaining Relevant Chunks: {len(filtered_chunks)}")
        for idx, chunk in enumerate(filtered_chunks, 1):
            section = getattr(chunk.metadata, 'section_title', 'N/A')
            print(f"--- Retained Chunk [{idx}] ---")
            print(f"Section: {section}")

        print("\n[PASS] Reasoning execution completed!\n")

    # Execute the test
    test_reasoning_filtering()