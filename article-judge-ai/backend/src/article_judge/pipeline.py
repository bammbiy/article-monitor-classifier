"""Orchestrates one link end-to-end: pick an extractor, extract, judge.

Both the CLI and the web API call process_one() for every link, so the
single-link and batch code paths (terminal or browser) can never drift
apart in behavior.
"""

from anthropic import Anthropic

from .extractors import get_extractor
from .judge import judge_content
from .models import JudgeResult


def process_one(idx: int, url: str, criteria: str, client: Anthropic) -> JudgeResult:
    try:
        extractor = get_extractor(url)
        content = extractor.extract(url)
    except Exception as e:
        return JudgeResult(
            no=idx + 1,
            url=url,
            source_type="unknown",
            source="",
            title="",
            decision="ERROR",
            error=str(e),
        )

    try:
        result = judge_content(content, criteria, client)
    except Exception as e:
        return JudgeResult(
            no=idx + 1,
            url=url,
            source_type=content.source_type,
            source=content.site,
            title=content.title,
            decision="ERROR",
            error=f"Judging failed: {e}",
        )

    return JudgeResult(
        no=idx + 1,
        url=url,
        source_type=content.source_type,
        source=content.site,
        title=content.title,
        decision=result.get("decision", "?"),
        topic=result.get("topic", ""),
        reason=result.get("reason", ""),
    )
