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
🚧 Phase 1 - Under development

**Configuration setup in .env for LLMs**
Refer .env.example for config details
# Cohere Embed v4 for embeddings
# Gemini 3.5-flash-lite for intent extraction, reasoning and generation


**Steps to initialize tool locally**
1. activate venv
source .venv/bin/activate

2. run fastAPI server (auto reload for changes)
cd backend
python -m uvicorn app.main:app --reload

3. serve angular frontend
cd frontend
ng serve
