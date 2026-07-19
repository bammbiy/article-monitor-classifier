"""
Shared logic: article extraction + AI-based judging.

Both judge.py (single URL) and judge_batch.py (many URLs) use this module.
The actual judging rules live in criteria.md, not here — edit that file
to define what "collect" vs "skip" means for your use case.
"""

import json
from pathlib import Path

import requests
import trafilatura
from bs4 import BeautifulSoup
from anthropic import Anthropic

BASE_DIR = Path(__file__).parent
CRITERIA_PATH = BASE_DIR / "criteria.md"
MODEL = "claude-sonnet-5"  # swap to "claude-haiku-4-5-20251001" for lower cost/latency

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def fetch_article(url: str) -> dict:
    """Extract title, source name, and body text from a URL."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch page: {e}")

    text = trafilatura.extract(html, url=url, include_comments=False)
    metadata = trafilatura.extract_metadata(html, default_url=url)

    title = metadata.title if metadata and metadata.title else None
    site = metadata.sitename if metadata and metadata.sitename else None

    # Fallback if trafilatura can't extract the body: just grab <p> tags
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

    return {
        "url": url,
        "title": title or "(title extraction failed)",
        "site": site or "(source extraction failed)",
        "text": text[:6000],  # truncate to save tokens
    }


def load_criteria() -> str:
    if not CRITERIA_PATH.exists():
        raise FileNotFoundError(f"{CRITERIA_PATH} not found.")
    return CRITERIA_PATH.read_text(encoding="utf-8")


def judge(article: dict, criteria: str, client: Anthropic = None) -> dict:
    """Decide whether a single article should be collected or skipped."""
    client = client or Anthropic()

    system_prompt = f"""You are an assistant that helps a user monitor news articles.
Based on the criteria below, decide whether the given article should be
COLLECTED (relevant to what the user wants to track) or SKIPPED (not relevant).

{criteria}

# Output format
Respond with ONLY the following JSON. No other text, no code fences.
{{"decision": "COLLECT or SKIP", "reason": "1-2 sentence justification", "topic": "one-line summary of the article's main topic"}}
"""

    user_prompt = f"""Source: {article['site']}
Title: {article['title']}

Body:
{article['text']}
"""

    resp = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = resp.content[0].text.strip()
    raw = raw.strip("`")
    if raw.lower().startswith("json"):
        raw = raw[4:].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"decision": "?", "reason": f"Failed to parse response: {raw}", "topic": ""}
