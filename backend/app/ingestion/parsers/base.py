from abc import ABC, abstractmethod

from app.schemas.chunk import Chunk

### Abstract Base class for release notes parsers
class ReleaseNotesParser(ABC):

    @abstractmethod
    def parse(self, text: str) -> list[Chunk]:
        pass