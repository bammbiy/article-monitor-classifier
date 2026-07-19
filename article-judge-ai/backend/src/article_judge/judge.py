"""Sends extracted content to Claude and gets back a COLLECT/SKIP verdict.

The rules Claude judges against are entirely defined by criteria.md — this
module only knows how to package content for the model and parse its
response, never what the rules actually say.
"""

import json

from anthropic import Anthropic

from .config import MODEL
from .models import ExtractedContent

_SYSTEM_PROMPT_TEMPLATE = """You are an assistant that helps a user monitor links (news articles, \
YouTube videos, and social posts). Based on the criteria below, decide whether \
the given content should be COLLECTED (relevant to what the user wants to track) \
or SKIPPED (not relevant).

{criteria}

# Output format
Respond with ONLY the following JSON. No other text, no code fences.
{{"decision": "COLLECT or SKIP", "reason": "1-2 sentence justification", "topic": "one-line summary of the content's main topic"}}
"""


def _build_user_prompt(content: ExtractedContent) -> str:
    return (
        f"Type: {content.source_type}\n"
        f"Source: {content.site}\n"
        f"Title: {content.title}\n\n"
        f"Content:\n{content.body}"
    )


def _parse_response(raw_text: str) -> dict:
    cleaned = raw_text.strip().strip("`")
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"decision": "?", "reason": f"Failed to parse model response: {cleaned}", "topic": ""}


def judge_content(content: ExtractedContent, criteria: str, client: Anthropic | None = None) -> dict:
    """Returns a dict with 'decision', 'reason', 'topic'."""
    client = client or Anthropic()

    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=_SYSTEM_PROMPT_TEMPLATE.format(criteria=criteria),
        messages=[{"role": "user", "content": _build_user_prompt(content)}],
    )

    return _parse_response(response.content[0].text)
