from datetime import date, datetime, time, timezone
from app.ingestion.fetch import load_release_note
from app.ingestion.parsers.django import DjangoParser
from app.services.embed_store import ChromaReader, ChromaWriter
from app.services.cohere_client import embed_query


def main():

    # 1. Load and parse the release note
    file_path = "../data/raw/django/6.0.8.txt"
    print(f"Loading {file_path}...")
    raw_text = load_release_note(file_path)

    parser = DjangoParser()
    chunks = parser.parse(raw_text)
    print(f"Parsed {len(chunks)} chunks from 6.0.8.txt\n")

    # 2. Initialize ChromaWriter and persist chunks
    writer = ChromaWriter(collection_name="django_release_notes")
    total_stored = writer.store_chunks(chunks)
    print(f"\nStorage verification: Collection contains {total_stored} total documents.\n")

    # 3. Initialize ChromaReader for retrieval testing
    reader = ChromaReader(collection_name="django_release_notes")

    # --- Test 1: Semantic Search ---
    query_text = "What were the security fixes for spatial lookups?"
    print(f"--- Test 1: Semantic Search for '{query_text}' ---")
    query_vec = embed_query(query_text)
    semantic_results = reader.query_as_chunks(query_vector=query_vec, top_k_results=1)

    if semantic_results:
        top_chunk = semantic_results[0]
        print(f"Retrieved Section: {top_chunk.metadata.section_title}")
        print(f"Is Breaking: {top_chunk.metadata.is_breaking}")
        print(f"Release Date: {top_chunk.metadata.release_date}")
        print(f"Text Snippet:\n{top_chunk.text[:250]}...\n")

    # --- Test 2: Timestamp & Metadata Filter Search ---
    # Query for breaking changes released on or after January 1, 2026
    target_date = date(2026, 1, 1)
    target_ts = int(datetime.combine(target_date, time.min, tzinfo=timezone.utc).timestamp())

    print(f"\n--- Test 2: Filtered Query (is_breaking=True & release_date_ts >= {target_ts}) ---")
    filtered_results = reader.query_as_chunks(
        query_vector=query_vec,
        top_k_results=5,
        where={
            "$and": [
                {"release_date_ts": {"$gte": target_ts}},
                {"is_breaking": True}
            ]
        }
    )

    print(f"Found {len(filtered_results)} matching breaking chunks:")
    for i, res in enumerate(filtered_results, 1):
        print(f"[{i}] {res.metadata.section_title} | Date: {res.metadata.release_date}")

    # --- Test 3: Version Range Filter Search ---
    # Query for breaking changes in Django version 6.0.0 or higher
    print(f"\n--- Test 3: Filtered Query (version >= 6.0.0 & is_breaking=True) ---")
    version_filtered_results = reader.query_as_chunks(
        query_vector=query_vec,
        top_k_results=5,
        where={
            "$and": [
                {"version_major": {"$gte": 6}},
                {"version_minor": {"$gte": 0}},
                {"is_breaking": True}
            ]
        }
    )

    print(f"Found {len(version_filtered_results)} matching chunks:")
    for i, res in enumerate(version_filtered_results, 1):
        print(f"[{i}] {res.metadata.section_title} | Version: {res.metadata.version} | Breaking: {res.metadata.is_breaking}")


if __name__ == "__main__":
    main()