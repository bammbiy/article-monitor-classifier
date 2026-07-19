#!/usr/bin/env python3
"""
Article Judge AI - command-line interface.

Usage:
    article-judge single "https://example.com/article"
    article-judge batch links.txt
    article-judge batch                  # paste links directly, Ctrl+D/Ctrl+Z to finish

(If running from source without installing the package, use:
    python -m article_judge.cli single "https://..."
 instead of the `article-judge` command.)
"""

import argparse
import csv
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from .config import MAX_WORKERS
from .criteria import load_criteria
from .models import JudgeResult
from .pipeline import process_one

load_dotenv()

_DECISION_LABEL = {"COLLECT": "✅ Collect", "SKIP": "❌ Skip"}

_CSV_FIELDS = ["no", "decision", "source_type", "source", "title", "topic", "reason", "url", "error"]


def _require_api_key() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "ANTHROPIC_API_KEY is not set.\n"
            "Create a .env file next to criteria.md with: ANTHROPIC_API_KEY=sk-ant-..."
        )


def _print_result(r: JudgeResult) -> None:
    label = _DECISION_LABEL.get(r.decision, f"❓ {r.decision}")
    print("=" * 50)
    print(f"Type     : {r.source_type}")
    print(f"Source   : {r.source}")
    print(f"Title    : {r.title}")
    print("-" * 50)
    print(f"Decision : {label}")
    print(f"Topic    : {r.topic}")
    print(f"Reason   : {r.reason}")
    if r.error:
        print(f"Error    : {r.error}")
    print("=" * 50)


def cmd_single(args: argparse.Namespace) -> None:
    _require_api_key()
    criteria = load_criteria()
    result = process_one(0, args.url, criteria, Anthropic())
    _print_result(result)


def _read_urls(source: str | None) -> list[str]:
    if source and Path(source).exists():
        raw_lines = Path(source).read_text(encoding="utf-8").splitlines()
    else:
        print("Paste one URL per line.")
        print("When done: Ctrl+D on Mac/Linux, or Ctrl+Z then Enter on Windows.\n")
        raw_lines = sys.stdin.read().splitlines()

    urls: list[str] = []
    seen: set[str] = set()
    for line in raw_lines:
        u = line.strip()
        if not u or u.startswith("#"):
            continue
        if u not in seen:  # de-dupe, preserve order
            seen.add(u)
            urls.append(u)
    return urls


def cmd_batch(args: argparse.Namespace) -> None:
    _require_api_key()
    urls = _read_urls(args.file)
    if not urls:
        sys.exit("No links to judge.")

    print(f"Processing {len(urls)} link(s)...\n")
    criteria = load_criteria()
    client = Anthropic()

    results: list[JudgeResult] = [None] * len(urls)  # type: ignore
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(process_one, i, url, criteria, client): i for i, url in enumerate(urls)
        }
        done = 0
        for future in as_completed(futures):
            i = futures[future]
            results[i] = future.result()
            done += 1
            r = results[i]
            label = _DECISION_LABEL.get(r.decision, f"❓ {r.decision}")
            print(f"[{done}/{len(urls)}] {label} [{r.source_type}] {r.title or r.url}")

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    collect_count = sum(1 for r in results if r.decision == "COLLECT")
    skip_count = sum(1 for r in results if r.decision == "SKIP")
    err_count = len(results) - collect_count - skip_count
    print(f"✅ Collect: {collect_count}  /  ❌ Skip: {skip_count}  /  ❓ Error/review: {err_count}\n")

    out_path = Path(f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for r in results:
            writer.writerow(r.to_dict())

    print(f"Saved CSV: {out_path.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Judge whether links should be collected or skipped.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_single = sub.add_parser("single", help="Judge a single link")
    p_single.add_argument("url")
    p_single.set_defaults(func=cmd_single)

    p_batch = sub.add_parser("batch", help="Judge many links at once")
    p_batch.add_argument(
        "file", nargs="?", default=None, help="Text file with one URL per line (omit to paste directly)"
    )
    p_batch.set_defaults(func=cmd_batch)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
