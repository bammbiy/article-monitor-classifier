"""Every link type (article, YouTube, social post, ...) gets its own
Extractor. The rest of the app only depends on this interface, so adding a
new link type later means adding one file here and one line in registry.py —
nothing else changes.
"""

from abc import ABC, abstractmethod

from ..models import ExtractedContent


class BaseExtractor(ABC):
    @staticmethod
    @abstractmethod
    def matches(url: str) -> bool:
        """Return True if this extractor knows how to handle the URL."""

    @abstractmethod
    def extract(self, url: str) -> ExtractedContent:
        """Fetch the URL and return its extracted content.

        Raise RuntimeError with a user-facing message on failure.
        """
