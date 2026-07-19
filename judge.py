#!/usr/bin/env python3
"""
Article Judge AI - decide whether a single article should be collected or skipped.

To process many links at once, use judge_batch.py instead.

Usage:
    python judge.py "https://example.com/news/123"

Setup:
    Create a .env file in this folder with your API key:
        ANTHROPIC_API_KEY=sk-ant-...

The judging rules live in criteria.md. Edit that file to change what
"collect" vs "skip" means for your use case — no need to touch this script.
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from common import fetch_article, judge, load_criteria

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="Judge whether a single article URL should be collected or skipped."
    )
    parser.add_argument("url", help="Article URL to judge")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "ANTHROPIC_API_KEY is not set.\n"
            "Create a .env file in this folder with: ANTHROPIC_API_KEY=sk-ant-..."
        )

    try:
        article = fetch_article(args.url)
    except RuntimeError as e:
        sys.exit(f"[Error] {e}")

    criteria = load_criteria()
    result = judge(article, criteria)

    decision = result.get("decision", "?")
    label = {"COLLECT": "✅ Collect", "SKIP": "❌ Skip"}.get(decision, "❓ Needs review")

    print("=" * 50)
    print(f"Source   : {article['site']}")
    print(f"Title    : {article['title']}")
    print("-" * 50)
    print(f"Decision : {label}")
    print(f"Topic    : {result.get('topic', '')}")
    print(f"Reason   : {result.get('reason', '')}")
    print("=" * 50)


if __name__ == "__main__":
    main()
