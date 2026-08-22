from pydantic import BaseModel
from datetime import date

## For metadata filtering in the vector store
## is_breaking (changes backward comptabile/incompatible are false/true)
## True  = confirmed breaking
## False = confirmed non-breaking
class ChunkMetadata(BaseModel):
    technology: str
    version: str
    version_major: int
    version_minor: int
    version_patch: int
    release_date: date | None
    release_date_ts: int = 0
    is_breaking: bool
    section_title: str

    @model_validator(mode="after")
    jdef compute_timestamp(self) -> "ChunkMetadata":
        """Automatically calculates release_date_ts if release_date is present."""
        if self.release_date and not self.release_date_ts:
            dt = datetime.combine(self.release_date, time.min, tzinfo=timezone.utc)
            self.release_date_ts = int(dt.timestamp())
        return self

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