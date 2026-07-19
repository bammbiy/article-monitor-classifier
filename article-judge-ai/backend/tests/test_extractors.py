"""These test the URL-routing logic only (matches()), not live network
extraction — CI shouldn't depend on YouTube/news sites being reachable.
"""

from article_judge.extractors.article import ArticleExtractor
from article_judge.extractors.registry import get_extractor
from article_judge.extractors.social import SocialExtractor
from article_judge.extractors.youtube import YoutubeExtractor, extract_video_id


def test_youtube_matches_standard_watch_url():
    assert YoutubeExtractor.matches("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_youtube_matches_short_url():
    assert YoutubeExtractor.matches("https://youtu.be/dQw4w9WgXcQ")


def test_youtube_does_not_match_article_url():
    assert not YoutubeExtractor.matches("https://example.com/news/1")


def test_social_matches_known_domains():
    assert SocialExtractor.matches("https://x.com/anthropic/status/123")
    assert SocialExtractor.matches("https://www.instagram.com/p/abc123/")


def test_social_does_not_match_article_url():
    assert not SocialExtractor.matches("https://example.com/news/1")


def test_article_extractor_is_catch_all():
    # By design this always matches — it's the fallback.
    assert ArticleExtractor.matches("https://anything-at-all.example/x")


def test_video_id_extraction_variants():
    cases = {
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s": "dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ": "dQw4w9WgXcQ",
        "https://example.com/not-a-video": None,
    }
    for url, expected in cases.items():
        assert extract_video_id(url) == expected


def test_registry_routes_by_domain():
    assert isinstance(get_extractor("https://youtu.be/dQw4w9WgXcQ"), YoutubeExtractor)
    assert isinstance(get_extractor("https://x.com/anthropic/status/1"), SocialExtractor)
    assert isinstance(get_extractor("https://example.com/some/article"), ArticleExtractor)
