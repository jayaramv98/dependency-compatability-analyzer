import argparse
from pathlib import Path
from datetime import date, datetime, time, timezone
from app.ingestion.fetch import load_release_note
from app.ingestion.parsers.django import DjangoParser
from app.services.embed_store import ChromaReader, ChromaWriter
from app.services.cohere_client import embed_query


def main():
    # Setup configurable path via argparse
    arg_parser = argparse.ArgumentParser(description="Ingest release notes into Chroma DB.")
    arg_parser.add_argument(
        "--data-dir", 
        type=str, 
        default="../data/raw/django/", 
        help="Path to the directory containing raw release notes."
    )
    args = arg_parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists() or not data_dir.is_dir():
        print(f"Error: The directory {data_dir} does not exist or is not a directory.")
        return

    parser = DjangoParser()
    all_chunks = []

    # 1. Loop over each .txt file in the directory and parse
    print(f"Scanning directory: {data_dir}\n")
    for file_path in data_dir.glob("*.txt"):
        print(f"Loading {file_path}...")
        raw_text = load_release_note(str(file_path))
        chunks = parser.parse(raw_text)
        all_chunks.extend(chunks)
        print(f"Parsed {len(chunks)} chunks from {file_path.name}")

    print(f"\nTotal chunks parsed across all files: {len(all_chunks)}")

    # 2. Initialize ChromaWriter and persist chunks efficiently
    writer = ChromaWriter(collection_name="django_release_notes")
    if all_chunks:
        total_stored = writer.store_chunks(all_chunks)
        print(f"\nStorage verification: Collection contains {total_stored} total documents.\n")
    else:
        print("\nNo chunks to store.")

if __name__ == "__main__":
    main()