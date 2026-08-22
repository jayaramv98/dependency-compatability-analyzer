from fastapi import FastAPI
from app.config import settings
from app.schemas.query import QueryRequest, QueryResponse
from app.routes.query import router as query_router


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)

app.include_router(query_router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}