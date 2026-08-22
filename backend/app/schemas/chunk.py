from pydantic import BaseModel
from datetime import date

## For metadata filtering in the vector store
## is_breaking (changes backward comptabile are false, non-compatible are true, None if unclassified)
## True  = confirmed breaking
## False = confirmed non-breaking
## None  = unknown / not classified
class ChunkMetadata(BaseModel):
    technology: str
    version: str
    version_major: int
    version_minor: int
    version_patch: int
    release_date: date | None
    is_breaking: bool
    section_title: str

## For actual embedding in the vector store
class Chunk(BaseModel):
    text: str
    metadata: ChunkMetadata

"""
Sample chunk
{
  "text": "Context: Django 6.0.8 > Bugfixes\n\nFixed a regression in Django 6.0 that caused meth - django.db.models.query.QuerySet.bulk_create to crash on databases that support returning rows from bulk inserts when a related object providing the primary key was saved after assignment (ticket - 37234).",
  "metadata": {
    "technology": "django",
    "version": "6.0.8",
    "version_major": 6,
    "version_minor": 0,
    "version_patch": 8,
    "release_date": "2026-08-04",
    "is_breaking": false,
    "section_title": "Bugfixes"
  }
}
"""