from app.ingestion.fetch import load_release_note
from app.ingestion.clean import clean_text


raw_text = load_release_note("../data/raw/python-3.12-test.txt")
cleaned_text = clean_text(raw_text)

print("RAW:")
print(raw_text)

print("\nCLEANED:")
print(cleaned_text)