import hashlib
from datetime import date, datetime, time, timezone
from typing import List, Optional
import chromadb

from app.schemas.chunk import Chunk, ChunkMetadata
from app.services.cohere_client import embed_documents


class ChromaStore:
    def __init__(self, collection_name: str = "django_release_notes"):
        # Persistent local storage
        ## TODO - Update to use Chroma Cloud Storage in v2
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        
        # Initialize collection with cosine distance
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def _generate_chunk_id(self, text: str, version: str) -> str:
        """Generates a deterministic SHA-256 ID for idempotency."""
        hash_input = f"{version}-{text}".encode("utf-8")
        return hashlib.sha256(hash_input).hexdigest()

    def _to_chroma_metadata(self, metadata: ChunkMetadata) -> dict:
        """
        Converts Pydantic ChunkMetadata into a ChromaDB-compatible dictionary,
        guaranteeing release_date_ts is populated as an integer timestamp.
        """
        raw_dict = metadata.model_dump()
        rel_date = metadata.release_date

        timestamp = 0
        date_str = "unknown"

        if rel_date is not None:
            if isinstance(rel_date, str):
                try:
                    rel_date = datetime.strptime(rel_date, "%Y-%m-%d").date()
                except ValueError:
                    rel_date = None

            if isinstance(rel_date, date):
                dt = datetime.combine(rel_date, time.min, tzinfo=timezone.utc)
                timestamp = int(dt.timestamp())
                date_str = rel_date.isoformat()

        raw_dict["release_date"] = date_str
        raw_dict["release_date_ts"] = timestamp
        
        return raw_dict

    def _from_chroma_metadata(self, meta_dict: dict) -> ChunkMetadata:
        """
        Reconstructs a strict Pydantic ChunkMetadata instance from ChromaDB metadata.
        """
        cleaned_dict = dict(meta_dict)
        
        # Re-hydrate date from timestamp if available
        ts = cleaned_dict.pop("release_date_ts", 0)
        if ts and ts > 0:
            cleaned_dict["release_date"] = datetime.fromtimestamp(ts, tz=timezone.utc).date()
        else:
            date_str = cleaned_dict.get("release_date")
            if date_str and date_str != "unknown":
                try:
                    cleaned_dict["release_date"] = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    cleaned_dict["release_date"] = None
            else:
                cleaned_dict["release_date"] = None

        return ChunkMetadata(**cleaned_dict)

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
                # FIXED: Now explicitly calling _to_chroma_metadata to include release_date_ts
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

    def query_as_chunks(
        self,
        query_vector: List[float],
        n_results: int = 5,
        where: Optional[dict] = None
    ) -> List[Chunk]:
        """
        Queries ChromaDB with optional metadata filtering and returns Pydantic Chunk objects.
        """
        query_args = {
            "query_embeddings": [query_vector],
            "n_results": n_results
        }
        if where:
            query_args["where"] = where

        results = self.collection.query(**query_args)

        retrieved_chunks: List[Chunk] = []
        if results["documents"] and results["documents"][0]:
            docs = results["documents"][0]
            metas = results["metadatas"][0]

            for doc_text, meta_dict in zip(docs, metas):
                metadata_model = self._from_chroma_metadata(meta_dict)
                retrieved_chunks.append(Chunk(text=doc_text, metadata=metadata_model))

        return retrieved_chunks