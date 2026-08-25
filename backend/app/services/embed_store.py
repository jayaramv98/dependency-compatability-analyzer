import hashlib
from typing import List, Optional
import chromadb

from app.schemas.chunk import Chunk, ChunkMetadata
from app.services.cohere_client import embed_documents
from app.config import settings

## Currently we use persistent(local) storage
## TODO - update to use Chroma Cloud Storage in v2

# handles insertion into chroma-DB
class ChromaWriter:
    def __init__(self, collection_name: str = settings.django_chroma_collection or "django_release_notes"):
        self.client = chromadb.PersistentClient(path=settings.local_chroma_db_path)
        self.collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    ### generates a unique hash value for idempotency and deduplication
    def _generate_chunk_id(self, text: str, version: str) -> str:
        """Generates a deterministic SHA-256 ID for idempotency."""
        hash_input = f"{version}-{text}".encode("utf-8")
        return hashlib.sha256(hash_input).hexdigest()

    ### method to convert pyndantic schema of metadata JSON to chroma-DB dictionary (on insertion)
    def _to_chroma_metadata(self, metadata: ChunkMetadata) -> dict:
        """
        Converts Pydantic ChunkMetadata into a ChromaDB-compatible dictionary.
        Leverages Pydantic's pre-computed fields for clean serialization.
        """
        raw_dict = metadata.model_dump()

        # Ensure ChromaDB compatibility for date fields
        if metadata.release_date is not None:
            raw_dict["release_date"] = metadata.release_date.isoformat()
        else:
            # explicitly store None date as unknown for grounded results
            raw_dict["release_date"] = "unknown"

        # Explicitly ensure numeric version fields and timestamp are primitive ints
        ## These metadata fields are the primary filtering options for querying relevant chunks/vectors
        raw_dict["version_major"] = int(metadata.version_major)
        raw_dict["version_minor"] = int(metadata.version_minor)
        raw_dict["version_patch"] = int(metadata.version_patch)
        raw_dict["release_date_ts"] = int(metadata.release_date_ts)

        return raw_dict

    # Main function which actually stores logically chunked data vectors & metadata into the DB collection
    # Cohere embed model v4.0 supports 2000 chunks/docs per API call
    # TODO cohere's embed v4.0 model - add syntax & limits
    def store_chunks(self, chunks: List[Chunk], batch_size: int = 500) -> int:
        """Batches chunks, embeds via Cohere service, and stores them in ChromaDB."""
        if not chunks:
            print("No chunks provided to store.")
            return 0

        print(f"Starting vector ingestion for {len(chunks)} chunks...")

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            print(f"Embedding and storing batch {i + 1} to {i + len(batch)}...")

            documents: List[str] = []
            metadatas: List[dict] = []
            ids: List[str] = []

            for chunk in batch:
                documents.append(chunk.text)
                metadatas.append(self._to_chroma_metadata(chunk.metadata))
                ids.append(self._generate_chunk_id(chunk.text, chunk.metadata.version))

            embeddings = embed_documents(texts=documents)

            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )

        total_count = self.collection.count()
        print(f"Ingestion complete. Total items in collection: {total_count}")
        return total_count

# handles querying/searching - vector similarity, metadata filtering from chroma-DB
class ChromaReader:
    def __init__(self, collection_name: str = settings.django_chroma_collection or "django_release_notes"):
        self.client = chromadb.PersistentClient(path=settings.local_chroma_db_path)
        self.collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    # method to convert chroma-DB metadata dictionary back to pydantic schema model (on retrieval)
    def _from_chroma_metadata(self, meta_dict: dict) -> ChunkMetadata:
        """
        Reconstructs a strict Pydantic ChunkMetadata instance from ChromaDB metadata.
        (Pydantic's validator will automatically handle any missing timestamp re-syncing if needed).
        """
        return ChunkMetadata(**meta_dict)

    # method to query the vectors (similarity search + metadata filtering) from the collection
    def query_as_chunks(
        self,
        query_vector: List[float],
        top_k_results: int = 5,
        where: Optional[dict] = None
    ) -> List[Chunk]:
        """
        Queries ChromaDB with optional metadata filtering and returns Pydantic Chunk objects.
        """
        query_args = {
            "query_embeddings": [query_vector],
            "n_results": top_k_results,
            "include": ["documents", "metadatas", "distances"]
        }
        if where:
            query_args["where"] = where

        """
        TODO - in v2
        Leveraging where_document allows you to combine semantic vector search (via query_embeddings),
        structured metadata filtering (via where for version and date ranges),
        and full-text/regex keyword matching (via where_document) all in a single query engine call.

        This ensures that your retrieval step is extraordinarily precise—filtering out noise structurally,
        textually, and semantically before the context ever hits your generation/LLM model.

        results = collection.query(
            query_embeddings=[query_vector],
            n_results=5,
            where={
                "$and": [
                    {"version_major": {"$gte": 6}},
                    {"is_breaking": True}
                ]
            },
            where_document={
                "$contains": "spatial lookups"
            }
        )

        """

        results = self.collection.query(**query_args)

        retrieved_chunks: List[Chunk] = []
        # Create a separate list for the scores
        distances: List[float] = []

        if results["documents"] and results["documents"][0]:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results.get("distances", [[0.0]])[0]

            for doc_text, meta_dict, dist in zip(docs, metas, dists):
                metadata_model = self._from_chroma_metadata(meta_dict)
                retrieved_chunks.append(Chunk(text=doc_text, metadata=metadata_model))
                distances.append(dist)

        # Return both as a tuple
        return retrieved_chunks, distances