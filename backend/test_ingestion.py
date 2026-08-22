from datetime import date, datetime, time, timezone
from app.ingestion.fetch import load_release_note
from app.ingestion.parsers.django import DjangoParser
from app.ingestion.embed_store import ChromaStore
from app.services.cohere_client import embed_query


def main():
    # 1. Load and parse the release note
    file_path = "../data/raw/django/6.0.8.txt"
    print(f"Loading {file_path}...")
    raw_text = load_release_note(file_path)

    parser = DjangoParser()
    chunks = parser.parse(raw_text)
    print(f"Parsed {len(chunks)} chunks from 6.0.8.txt\n")

    # 2. Initialize ChromaStore and persist chunks
    store = ChromaStore(collection_name="django_release_notes")
    total_stored = store.store_chunks(chunks)
    print(f"\nStorage verification: Collection contains {total_stored} total documents.\n")

    # 3. Test 1: Semantic Search
    query_text = "What were the security fixes for spatial lookups?"
    print(f"--- Test 1: Semantic Search for '{query_text}' ---")
    query_vec = embed_query(query_text)
    semantic_results = store.query_as_chunks(query_vector=query_vec, n_results=1)

    if semantic_results:
        top_chunk = semantic_results[0]
        print(f"Retrieved Section: {top_chunk.metadata.section_title}")
        print(f"Is Breaking: {top_chunk.metadata.is_breaking}")
        print(f"Release Date: {top_chunk.metadata.release_date}")
        print(f"Text Snippet:\n{top_chunk.text[:250]}...\n")

    # 4. Test 2: Timestamp & Metadata Filter Search
    # Query for breaking changes released on or after January 1, 2026
    target_date = date(2026, 1, 1)
    target_ts = int(datetime.combine(target_date, time.min, tzinfo=timezone.utc).timestamp())

    print(f"--- Test 2: Filtered Query (is_breaking=True & release_date_ts >= {target_ts}) ---")
    filtered_results = store.query_as_chunks(
        query_vector=query_vec,
        n_results=5,
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


if __name__ == "__main__":
    main()