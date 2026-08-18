"""Base extractor interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExtractionResult:
    """Result of text extraction from a file."""
    text: str = ""
    page_texts: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class BaseExtractor(ABC):
    """Abstract base class for file text extractors.

    Implement `extract()` to add support for new file types.
    Register via `engine.register_extractor(FileType, YourExtractor)`.
    """

    @abstractmethod
    def extract(self, file_path: Path) -> ExtractionResult:
        """Extract text content from a file.

        Args:
            file_path: Path to the source file.

        Returns:
            ExtractionResult with text content and optional page-level text.
        """
        ...
