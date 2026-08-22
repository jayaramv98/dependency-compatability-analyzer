from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Dependency Compatibility Analyzer"
    app_description: str = "RAG-powered dependency upgrade compatibility analyzer"
    app_version: str = "0.1.0"

    ## cohere embed api
    cohere_embed_api_url: str
    cohere_api_key: str
    cohere_embed_model: str

    # ChromaDB configs
    local_chroma_db_path: str = "./chroma_db"
    django_chroma_collection: str = "django_release_notes"
    
    ## reads configs from .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

settings = Settings()