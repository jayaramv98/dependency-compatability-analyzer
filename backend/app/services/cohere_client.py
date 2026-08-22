import cohere

from app.config import settings

client = cohere.ClientV2(
    api_key=settings.cohere_api_key
)

## function to embed the release notes/change logs into vectors
## Document:
 ##texts = list[str]
 ##input_type = search_document
 ##returns = list of vectors
def embed_documents(texts: list[str]):
    response = client.embed(
        texts=texts,
        model=settings.cohere_embed_model,
        input_type="search_document",
        embedding_types=["float"]
    )

    return response.embeddings.float


## function to embed the user question/query
## Query:
 ##texts = [single string]
 ##input_type = search_query
 ##returns = single vector
def embed_query(text: str):
    response = client.embed(
        texts=[text],
        model=settings.cohere_embed_model,
        input_type="search_query",
        embedding_types=["float"]
    )

    return response.embeddings.float[0]