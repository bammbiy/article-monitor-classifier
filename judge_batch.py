#!/usr/bin/env python3
"""
Article Judge AI (batch mode) - judge many article links at once.

Usage:
    1) From a file (recommended for a lot of links)
       Paste one URL per line into links.txt, then:
           python judge_batch.py links.txt

    2) Paste directly into the terminal
       python judge_batch.py
       (paste one URL per line, then press Ctrl+D on Mac/Linux,
        or Ctrl+Z then Enter on Windows, when you're done)

Results print to the screen as they finish, and are also saved to a
CSV file in this folder so you can open them in Excel.
"""

import csv
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic

from common import fetch_article, judge, load_criteria

load_dotenv()

MAX_WORKERS = 5  # how many articles to process concurrently; lower this if you hit rate limits


def read_urls(source: str | None) -> list[str]:
    if source and Path(source).exists():
        raw_lines = Path(source).read_text(encoding="utf-8").splitlines()
    else:
        print("Paste one URL per line.")
        print("When done: Ctrl+D on Mac/Linux, or Ctrl+Z then Enter on Windows.\n")
        raw_lines = sys.stdin.read().splitlines()

    urls, seen = [], set()
    for line in raw_lines:
        u = line.strip()
        if not u or u.startswith("#"):
            continue
        if u not in seen:  # de-dupe while preserving order
            seen.add(u)
            urls.append(u)
    return urls


def process_one(idx: int, url: str, criteria: str, client: Anthropic) -> dict:
    try:
        article = fetch_article(url)
        result = judge(article, criteria, client)
        return {
            "no": idx + 1,
            "url": url,
            "source": article["site"],
            "title": article["title"],
            "decision": result.get("decision", "?"),
            "topic": result.get("topic", ""),
            "reason": result.get("reason", ""),
            "error": "",
        }
    except Exception as e:
        return {
            "no": idx + 1,
            "url": url,
            "source": "",
            "title": "",
            "decision": "ERROR",
            "topic": "",
            "reason": "",
            "error": str(e),
        }


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "ANTHROPIC_API_KEY is not set.\n"
            "Create a .env file in this folder with: ANTHROPIC_API_KEY=sk-ant-..."
        )

    source = sys.argv[1] if len(sys.argv) > 1 else None
    urls = read_urls(source)

    if not urls:
        sys.exit("No links to judge.")

    print(f"Processing {len(urls)} link(s)...\n")

    criteria = load_criteria()
    client = Anthropic()

    results: list[dict] = [None] * len(urls)  # type: ignore
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(process_one, i, url, criteria, client): i
            for i, url in enumerate(urls)
        }
        done = 0
        for future in as_completed(futures):
            i = futures[future]
            results[i] = future.result()
            done += 1
            r = results[i]
            label = {"COLLECT": "✅ Collect", "SKIP": "❌ Skip"}.get(r["decision"], f"❓ {r['decision']}")
            print(f"[{done}/{len(urls)}] {label} - {r['title'] or r['url']}")

    # ---- Summary ----
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    collect_count = sum(1 for r in results if r["decision"] == "COLLECT")
    skip_count = sum(1 for r in results if r["decision"] == "SKIP")
    err_count = len(results) - collect_count - skip_count
    print(f"✅ Collect: {collect_count}  /  ❌ Skip: {skip_count}  /  ❓ Error/review: {err_count}\n")

    for r in results:
        mark = {"COLLECT": "✅", "SKIP": "❌"}.get(r["decision"], "❓")
        print(f"{mark} [{r['source'] or '?'}] {r['title'] or r['url']}")
        if r["error"]:
            print(f"    └ Error: {r['error']}")

    # ---- CSV export (utf-8-sig so Excel doesn't mangle non-ASCII text) ----
    out_path = Path(f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f, fieldnames=["no", "decision", "source", "title", "topic", "reason", "url", "error"]
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"\nSaved CSV: {out_path.resolve()}")


if __name__ == "__main__":
    main()
