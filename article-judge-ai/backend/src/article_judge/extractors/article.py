"""Generic news/blog article extractor.

Also serves as the catch-all fallback for any URL no other extractor
claims — that's why matches() always returns True and it must stay last
in the registry's extractor list.
"""

import requests
import trafilatura
from bs4 import BeautifulSoup

from ..config import MAX_BODY_CHARS, REQUEST_TIMEOUT_SECONDS, USER_AGENT
from ..models import ExtractedContent
from .base import BaseExtractor

_HEADERS = {"User-Agent": USER_AGENT}


class ArticleExtractor(BaseExtractor):
    @staticmethod
    def matches(url: str) -> bool:
        return True  # generic fallback — keep last in registry order

    def extract(self, url: str) -> ExtractedContent:
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
            resp.raise_for_status()
            html = resp.text
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch page: {e}")

        text = trafilatura.extract(html, url=url, include_comments=False)
        metadata = trafilatura.extract_metadata(html, default_url=url)

        title = metadata.title if metadata and metadata.title else None
        site = metadata.sitename if metadata and metadata.sitename else None

        # trafilatura sometimes can't find a clean article body (unusual page
        # layout, thin content). Fall back to grabbing every <p> tag.
        if not text:
            soup = BeautifulSoup(html, "html.parser")
            paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
            text = "\n".join(p for p in paragraphs if len(p) > 20)
            if not title and soup.title:
                title = soup.title.get_text(strip=True)

        if not text:
            raise RuntimeError(
                "Could not extract article body. The page may require a login, "
                "sit behind a paywall, or render its content via JavaScript."
            )

        return ExtractedContent(
            url=url,
            source_type="article",
            site=site or "(source extraction failed)",
            title=title or "(title extraction failed)",
            body=text[:MAX_BODY_CHARS],
        )
