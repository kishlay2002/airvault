from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ExtractionResult:
    text: str
    page_texts: list[str] | None = None
    metadata: dict | None = None


class BaseExtractor(ABC):
    @abstractmethod
    async def extract(self, file_path: str) -> ExtractionResult:
        """Extract text content from a file.

        Args:
            file_path: Absolute path to the file.

        Returns:
            ExtractionResult with extracted text and optional per-page breakdown.
        """
        ...
