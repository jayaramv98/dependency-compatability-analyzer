# Extracts query terms, versions, operators, and breaking change flags.
from typing import Optional, Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings

## We will put the intent logic here
## Responsible for extracting the intent of the user question/query
## And creating the search query for the retrieval node

from app.agent.state import QueryState

# --- 1. Pydantic Schema for Structured Output ---
class IntentResponse(BaseModel):
    """Structured output from the routing LLM to update the QueryState."""
    search_query: str = Field(
        description=(
            "The specific technical concept, feature, or bug to search for. "
            "DO NOT include framework names (e.g., 'Django'), version numbers (e.g., '6.0.8'), "
            "or generic words like 'release notes' or 'breaking changes'. Focus purely on the semantic topic."
            )
        )
    technology: str = Field(
        description="The framework or language being asked about (e.g., 'django', 'angular', 'fastapi'). Default to 'django' if unspecified.",
        default="django"
    )

    # Single version filters (if they just ask about one version)
    version_major: Optional[int] = Field(
        description="The major version number if specified (e.g., 6 for '6.0.8').",
        default=None
    )
    version_minor: Optional[int] = Field(
        description="The minor version number if specified (e.g., 0 for '6.0.8').",
        default=None
    )
    version_patch: Optional[int] = Field(
        description="The patch version number if specified (e.g., 8 for '6.0.8').",
        default=None
    )

    # operator for single version filtering
    version_operator: Literal["==", ">=", "<=", ">", "<"] = Field(
        description="The version filter operator. Use '>=' for words like 'since', 'after', or 'newer than'. Use '<=' for 'before' or 'older than'. Default is '=='.",
        default="=="
    )
    
    # Range boundaries (for upgrading or comparing versions)
    current_version_major: Optional[int] = Field(
        description="The starting/current major version if the user specifies an upgrade path.",
        default=None
    )
    current_version_minor: Optional[int] = Field(
        description="The starting/current minor version if the user specifies an upgrade path.",
        default=None
    )
    current_version_patch: Optional[int] = Field(
        description="The starting/current patch version if the user specifies an upgrade path.",
        default=None
    )
    target_version_major: Optional[int] = Field(
        description="The destination/target major version if the user specifies an upgrade path.",
        default=None
    )
    target_version_minor: Optional[int] = Field(
        description="The destination/target minor version if the user specifies an upgrade path.",
        default=None
    )
    target_version_patch: Optional[int] = Field(
        description="The destination/target patch version if the user specifies an upgrade path.",
        default=None
    )

    # backwards incompatible changes (True/False)
    is_breaking: Optional[bool] = Field(
        description="Set to True ONLY if the user explicitly asks about breaking changes, backward incompatibilities, or upgrade hazards. Otherwise None.",
        default=None
    )

# --- 2. Prompt Template ---
INTENT_SYSTEM_PROMPT = """You are an expert technical search routing assistant. 
Analyze the user's software question and extract precise filtering intents.

1. REWRITE RULES:
   - Extract the core technical topic, API, setting, or bug into `search_query`.
   - If the user asks a broad question without a specific feature (e.g., "What changed in 6.0?"), set `search_query` to "summary of changes and updates".
   - NEVER include framework names, version numbers, or words like "release notes" in `search_query` (these are handled by metadata filters).

2. METADATA EXTRACTION:
   - Extract framework into `technology` (lowercase).
   - Extract major, minor, patch numbers into respective integer fields.
   - Extract version comparison operators ('>=', '<=', '==').
   - Set `is_breaking=True` if breaking changes or deprecations or incompatible are mentioned.

User Question: {question}
"""

# system - The instructions, rules, and persona. The LLM treats this as its core programming
# human - The actual input, query, or command from the person interacting with the model.
router_prompt = ChatPromptTemplate.from_messages([
    ("system", INTENT_SYSTEM_PROMPT),
    ("human", "{question}")
])
# By defining ("human", "{question}"), you are telling the prompt template:
# "When I pass you a dictionary with the key 'question',
# inject its value right here, and label it as a message coming from the human."

# --- 3. Gemini LLM & Chain Initialization ---
# Gemini 1.5 Flash is ideal for rapid, structured intent routing. 
## Use gemini-3.1-pro-preview model for accurate, high reasoning (v2)
llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash", 
    api_key=settings.gemini_api_key,
    temperature=0  # Zero temperature for deterministic extraction
)

# Bind the Pydantic schema to force structured output
structured_llm = llm.with_structured_output(IntentResponse)

# Chain the prompt and the LLM
# This is called LCEL (LangChain Expression Language)
# It passes data from left to right.
router_chain = router_prompt | structured_llm

# --- 4. The LangGraph Node Function ---
def route_query(state: QueryState) -> dict:
    """
    Analyzes the incoming question, extracts structured routing intents via Gemini, 
    and returns a dictionary that LangGraph uses to update the state.
    """
    print("--- ROUTER NODE: Extracting Intents via Gemini ---")
    question = state["question"]
    
    # Invoke the Gemini chain to parse the question
    # Input: The dictionary {"question": "..."} enters the left side of the pipe.
    
    # The Prompt: router_prompt catches that dictionary, 
    # finds the {question} placeholder, and injects your text to create a complete,
    # formatted prompt string.

    # The LLM: That formatted prompt string is then piped to structured_llm on the right side. 
    # The LLM reads the prompt and generates the structured JSON output.
    result: IntentResponse = router_chain.invoke({"question": question})
    
    print(f" > Rewritten Query: '{result.search_query}'")
    print(
        f" > Filters: Tech={result.technology}, "
        f"v{result.version_major}.{result.version_minor}.{result.version_patch}, "
        f"current_version{result.current_version_major}.{result.current_version_minor}.{result.current_version_patch}, "
        f"target_version{result.target_version_major}.{result.target_version_minor}.{result.target_version_patch}, "
        f"Breaking={result.is_breaking}/n"
    )
    
    # LangGraph automatically merges this dictionary back into the QueryState
    return {
        "search_query": result.search_query,
        "technology": result.technology,

        "version_major": result.version_major,
        "version_minor": result.version_minor,
        "version_patch": result.version_patch,

        "version_operator": result.version_operator,

        "current_version_major": result.current_version_major,
        "current_version_minor": result.current_version_minor,
        "current_version_patch": result.current_version_patch,
        "target_version_major": result.target_version_major,
        "target_version_minor": result.target_version_minor,
        "target_version_patch": result.target_version_patch,

        "is_breaking": result.is_breaking
    }


##### Node test script
##### Run "python -m app.agent.nodes.router"
if __name__ == "__main__":
    # Create a mock QueryState dictionary
    test_state = {
        "question": "What are the spatial lookup changes in Django 6.0.8?"
    }
    
    print(f"Testing with input: {test_state['question']}\n")
    
    # Run the router node
    output_state = route_query(test_state)
    
    print("\n--- Final Output Dictionary ---")
    import json
    print(json.dumps(output_state, indent=2))