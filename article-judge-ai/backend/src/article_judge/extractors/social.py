"""Social platform extractor: reads Open Graph meta tags (og:title,
og:description, og:site_name) — the same data platforms serve to unfurl
link previews in chat apps and feeds.

Honest limitation: X/Twitter, Instagram, and similar platforms increasingly
require a login or their official API for full content, and sometimes block
even the OG preview for automated requests. When that happens this raises a
clear error rather than guessing — see README for details.
"""

import requests
from bs4 import BeautifulSoup

from ..config import REQUEST_TIMEOUT_SECONDS, USER_AGENT
from ..models import ExtractedContent
from .base import BaseExtractor

_HEADERS = {"User-Agent": USER_AGENT}

_SOCIAL_DOMAINS = (
    "twitter.com",
    "x.com",
    "instagram.com",
    "threads.net",
    "facebook.com",
    "tiktok.com",
    "reddit.com",
)


def _meta_content(soup: BeautifulSoup, *keys: str) -> str | None:
    for key in keys:
        tag = soup.find("meta", property=key) or soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return None


class SocialExtractor(BaseExtractor):
    @staticmethod
    def matches(url: str) -> bool:
        return any(domain in url for domain in _SOCIAL_DOMAINS)

    def extract(self, url: str) -> ExtractedContent:
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch page: {e}")

        soup = BeautifulSoup(resp.text, "html.parser")

        title = _meta_content(soup, "og:title") or (
            soup.title.get_text(strip=True) if soup.title else None
        )
        description = _meta_content(soup, "og:description", "description") or ""
        site = _meta_content(soup, "og:site_name") or "(social)"

        if not title:
            raise RuntimeError(
                "Could not read a preview for this link. Social platforms often "
                "require a login or their official API for full access."
            )

        body = description or "(No preview text available for this post.)"

        return ExtractedContent(
            url=url,
            source_type="social",
            site=site,
            title=title,
            body=body,
        )
