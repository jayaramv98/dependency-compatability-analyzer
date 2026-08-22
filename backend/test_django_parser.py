from app.ingestion.fetch import load_release_note
from app.ingestion.parsers.django import DjangoParser

# 1. Load the raw text
raw_text = load_release_note("../data/raw/django/1.1.2.txt")

# 2. Instantiate the parser
parser = DjangoParser()

# 3. Call the parse() method (Notice: no version argument passed!)
chunks = parser.parse(text=raw_text)

# 4. Print the results
print(f"Total chunks extracted: {len(chunks)}\n")

for i, chunk in enumerate(chunks, 1):
    print(f"--- Chunk {i} ---")
    print(chunk.model_dump_json(indent=2)) 
    print("\n")