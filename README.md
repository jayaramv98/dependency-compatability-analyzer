# Dependency Compatibility Analyzer

A RAG-powered tool that analyzes dependency and framework release notes
to identify breaking changes between versions.

## Architecture

- Frontend: Angular
- Backend: FastAPI
- Orchestration: LangGraph
- Embeddings: Cohere
- Vector Store: Chroma
- LLM: Gemini

## Status

🚧 Under development
## activate venv
source .venv/bin/activate
## run fastAPI server (auto reload for changes)
python -m uvicorn app.main:app --reload