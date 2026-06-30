from abc import ABC, abstractmethod
from typing import List
from src.models import RawFact

class BaseExtractor(ABC):
    @abstractmethod
    def can_extract(self, file_path: str, content: bytes) -> bool:
        """Return True if this extractor can handle the file."""
        pass

    @abstractmethod
    def extract(self, file_path: str, content: bytes) -> List[RawFact]:
        """Extract a list of raw facts from the file content."""
        pass
