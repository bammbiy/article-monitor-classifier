"""Routes a URL to the extractor that should handle it.

Order matters: specific extractors are checked first, and ArticleExtractor
is the generic catch-all that always matches, so it must stay last.
"""

from .article import ArticleExtractor
from .base import BaseExtractor
from .social import SocialExtractor
from .youtube import YoutubeExtractor

_EXTRACTORS: list[BaseExtractor] = [
    YoutubeExtractor(),
    SocialExtractor(),
    ArticleExtractor(),  # fallback — must be last
]


def get_extractor(url: str) -> BaseExtractor:
    for extractor in _EXTRACTORS:
        if extractor.matches(url):
            return extractor
    return _EXTRACTORS[-1]
