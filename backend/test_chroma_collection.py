from app.ingestion.embed_store import ChromaStore

# Initialize your store
store = ChromaStore(collection_name="django_release_notes")

# Fetch all records in the collection
data = store.collection.get(
    include=["documents", "metadatas"]
)

print(f"Total documents found: {len(data['ids'])}")
print("-" * 50)

# Loop through and print details of each stored chunk
for i, (doc_id, doc_text, meta) in enumerate(zip(data["ids"], data["documents"], data["metadatas"]), 1):
    print(f"[{i}] ID: {doc_id}")
    print(f"    Section Title : {meta.get('section_title')}")
    print(f"    Version       : {meta.get('version')}")
    print(f"    Release Date  : {meta.get('release_date')} (Timestamp: {meta.get('release_date_ts')})")
    print(f"    Is Breaking   : {meta.get('is_breaking')}")
    print(f"    Text Preview  : {doc_text[:120]}...\n")