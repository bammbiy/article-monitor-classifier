"""YouTube extractor: video title/channel via the public oEmbed endpoint
(no API key needed) plus the caption track via youtube-transcript-api, so
judging is based on what's actually said in the video, not just the title.
"""

import re

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api import YouTubeTranscriptApiException

from ..config import MAX_BODY_CHARS, REQUEST_TIMEOUT_SECONDS
from ..models import ExtractedContent
from .base import BaseExtractor

_ID_PATTERNS = [
    re.compile(r"youtu\.be/([A-Za-z0-9_-]{11})"),
    re.compile(r"youtube\.com/watch\?(?:.*&)?v=([A-Za-z0-9_-]{11})"),
    re.compile(r"youtube\.com/shorts/([A-Za-z0-9_-]{11})"),
    re.compile(r"youtube\.com/embed/([A-Za-z0-9_-]{11})"),
    re.compile(r"youtube\.com/live/([A-Za-z0-9_-]{11})"),
]

_TRANSCRIPT_LANGUAGES = ("ko", "en")


def extract_video_id(url: str) -> str | None:
    for pattern in _ID_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


def _fetch_metadata(video_id: str) -> tuple[str, str]:
    """Returns (title, channel_name). Falls back to placeholders on failure."""
    try:
        resp = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        return (
            data.get("title", "(title extraction failed)"),
            data.get("author_name", "(channel extraction failed)"),
        )
    except (requests.RequestException, ValueError):
        return "(title extraction failed)", "(channel extraction failed)"


def _fetch_transcript(video_id: str) -> str:
    """Returns the transcript text, or '' if captions aren't available."""
    try:
        fetched = YouTubeTranscriptApi().fetch(video_id, languages=_TRANSCRIPT_LANGUAGES)
        return " ".join(snippet.text for snippet in fetched.snippets)
    except YouTubeTranscriptApiException:
        return ""


class YoutubeExtractor(BaseExtractor):
    @staticmethod
    def matches(url: str) -> bool:
        return "youtube.com" in url or "youtu.be" in url

    def extract(self, url: str) -> ExtractedContent:
        video_id = extract_video_id(url)
        if not video_id:
            raise RuntimeError("Could not parse a YouTube video ID from this URL.")

        title, channel = _fetch_metadata(video_id)
        transcript = _fetch_transcript(video_id)

        if transcript:
            body = transcript[:MAX_BODY_CHARS]
        else:
            body = (
                "(No captions available for this video — judging from the "
                "title and channel name only.)"
            )

        return ExtractedContent(
            url=url,
            source_type="youtube",
            site=f"YouTube · {channel}",
            title=title,
            body=body,
        )
