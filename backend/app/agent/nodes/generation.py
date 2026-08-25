# app/agent/nodes/generation.py

### LLM node which formats the response back to the user

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from app.agent.state import QueryState

from app.config import settings

# --- 1. Structured Output Schema ---
class CompatibilityReport(BaseModel):
    summary: str = Field(
        description="Direct, technical answer summarizing the relevant changes."
    )
    breaking_changes: list[str] = Field(
        default_factory=list,
        description="List of breaking changes, deprecations, or backwards-incompatible shifts."
    )
    security_impact: list[str] = Field(
        default_factory=list,
        description="Security fixes or CVE mitigations present in the context."
    )
    developer_actions: list[str] = Field(
        default_factory=list,
        description="Actionable steps or code adjustments required for compatibility."
    )
    confidence_score: float = Field(
        description="Confidence between 0.0 and 1.0 based on available context sufficiency."
    )

# --- 2. Generation Prompt & LLM Setup ---
GENERATOR_PROMPT = """You are a technical software language and framework compatibility specialist.
Synthesize an accurate analysis strictly using the verified documentation chunks provided below.

Rules:
1. Ground all answers solely in the provided context. Do not invent details.
2. If breaking changes or CVEs are present, explicitly state their operational impacts.
3. Provide concrete developer guidance.

User Question:
{question}

Verified Documentation Chunks:
{context}
"""

prompt = ChatPromptTemplate.from_template(GENERATOR_PROMPT)

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    api_key=settings.gemini_api_key,
    temperature=0
).with_structured_output(CompatibilityReport)

generator_chain = prompt | llm

# --- 3. Node Function ---
def generate_answer(state: QueryState) -> dict:
    """
    Synthesizes relevant context chunks into a structured compatibility report
    and formats the final response string.
    """
    print("--- GENERATION NODE: Synthesizing Answer ---")
    question = state["question"]
    chunks = state.get("retrieved_chunks", [])

    if not chunks:
        print(" > No relevant chunks available for generation.")
        fallback_msg = "No relevant release notes or documentation chunks were found matching your query."
        return {"answer": fallback_msg}

    # Format the verified context
    formatted_context = "\n\n---\n\n".join(
        f"### Section: {getattr(chunk.metadata, 'section_title', 'Unknown')} (v{getattr(chunk.metadata, 'version', 'Unknown')})\n{chunk.text}"
        for chunk in chunks
    )

    # Invoke structured generator chain
    report: CompatibilityReport = generator_chain.invoke({
        "question": question,
        "context": formatted_context
    })

    # Render a structured Markdown report
    markdown_output = [
        f"### Summary\n{report.summary}\n",
    ]

    if report.breaking_changes:
        markdown_output.append("### ⚠️ Breaking Changes")
        for item in report.breaking_changes:
            markdown_output.append(f"- {item}")
        markdown_output.append("")

    if report.security_impact:
        markdown_output.append("### 🔒 Security Impacts & CVEs")
        for item in report.security_impact:
            markdown_output.append(f"- {item}")
        markdown_output.append("")

    if report.developer_actions:
        markdown_output.append("### 🛠️ Developer Guidance")
        for item in report.developer_actions:
            markdown_output.append(f"- {item}")
        markdown_output.append("")

    final_answer = "\n".join(markdown_output).strip()
    
    print(f" > Report generated (Confidence: {report.confidence_score}).\n")
    return {"answer": final_answer}


# --- 4. Isolated Unit Test ---
## Test script
## Run "python -m app.agent.nodes.generation"
if __name__ == "__main__":
    from app.services.embed_store import Chunk, ChunkMetadata

    def test_generation_execution():
        print("==================================================")
        print("RUNNING UNIT TEST: Generation Node Synthesis")
        print("==================================================")

        # Mock the single retained chunk from the reasoning node
        retained_chunk = Chunk(
            text=(
                "Spatial lookups allowed str and dict lookup values to be passed to "
                "django.contrib.gis.gdal.GDALRaster when they represented rasters. "
                "Depending on the raster driver, this could write a file to disk or issue a network request. "
                "The following types are now disallowed by spatial lookups: dict, and str that is not a valid "
                "GEOSGeometry. This is a backward incompatible change. All untrusted input should be validated."
            ),
            metadata=ChunkMetadata(
                technology="django",
                version="6.0.8",
                version_major=6,
                version_minor=0,
                version_patch=8,
                release_date="2026-03-01",
                is_breaking=True,
                section_title="CVE-2026-15307: Server-side file-write and request forgery via spatial lookups",
                url="https://docs.djangoproject.com/en/6.0/releases/6.0.8/"
            )
        )

        test_state: QueryState = {
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
            "retrieved_chunks": [retained_chunk],
            "answer": ""
        }

        print("Executing Generation Node with verified chunk...")
        result = generate_answer(test_state)

        print("\n==================================================")
        print("GENERATED REPORT OUTPUT:")
        print("==================================================")
        print(result["answer"])
        print("\n[PASS] Generation node unit test completed successfully!\n")

    test_generation_execution()