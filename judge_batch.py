#!/usr/bin/env python3
"""
중기부 온라인 모니터링 - 기사 링크 여러 개를 한 번에 판단하는 배치 스크립트

사용법:
    1) 파일로 넣기 (링크가 많을 때 추천)
       links.txt 에 링크를 한 줄에 하나씩 붙여넣고:
           python judge_batch.py links.txt

    2) 터미널에 바로 붙여넣기
       python judge_batch.py
       (링크를 한 줄에 하나씩 쫘라락 붙여넣고, 다 넣었으면
        Mac/Linux는 Ctrl+D, Windows는 Ctrl+Z 후 Enter)

결과는 화면에 요약으로 뜨고, 같은 폴더에 CSV 파일로도 저장됩니다.
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

MAX_WORKERS = 5  # 동시에 몇 개씩 처리할지. API 요청 제한에 걸리면 낮추세요.


def read_urls(source: str | None) -> list[str]:
    if source and Path(source).exists():
        raw_lines = Path(source).read_text(encoding="utf-8").splitlines()
    else:
        print("링크를 한 줄에 하나씩 붙여넣으세요.")
        print("다 넣었으면 Mac/Linux는 Ctrl+D, Windows는 Ctrl+Z 후 Enter.\n")
        raw_lines = sys.stdin.read().splitlines()

    urls, seen = [], set()
    for line in raw_lines:
        u = line.strip()
        if not u or u.startswith("#"):
            continue
        if u not in seen:  # 중복 링크 제거 (순서는 유지)
            seen.add(u)
            urls.append(u)
    return urls


def process_one(idx: int, url: str, criteria: str, client: Anthropic) -> dict:
    try:
        article = fetch_article(url)
        result = judge(article, criteria, client)
        return {
            "순번": idx + 1,
            "url": url,
            "매체": article["site"],
            "제목": article["title"],
            "판단": result.get("decision", "?"),
            "주제": result.get("topic", ""),
            "근거": result.get("reason", ""),
            "오류": "",
        }
    except Exception as e:
        return {
            "순번": idx + 1,
            "url": url,
            "매체": "",
            "제목": "",
            "판단": "오류",
            "주제": "",
            "근거": "",
            "오류": str(e),
        }


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "ANTHROPIC_API_KEY 가 설정되어 있지 않습니다.\n"
            "이 폴더에 .env 파일을 만들고 ANTHROPIC_API_KEY=sk-ant-... 를 넣어주세요."
        )

    source = sys.argv[1] if len(sys.argv) > 1 else None
    urls = read_urls(source)

    if not urls:
        sys.exit("판단할 링크가 없습니다.")

    print(f"총 {len(urls)}개 링크 처리 시작...\n")

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
            label = {"O": "⭕ 수집", "X": "❌ 제외"}.get(r["판단"], f"❓ {r['판단']}")
            print(f"[{done}/{len(urls)}] {label} - {r['제목'] or r['url']}")

    # ---- 요약 ----
    print("\n" + "=" * 70)
    print("결과 요약")
    print("=" * 70)
    o_count = sum(1 for r in results if r["판단"] == "O")
    x_count = sum(1 for r in results if r["판단"] == "X")
    err_count = len(results) - o_count - x_count
    print(f"⭕ 수집 {o_count}건  /  ❌ 제외 {x_count}건  /  ❓ 오류·확인필요 {err_count}건\n")

    for r in results:
        mark = {"O": "⭕", "X": "❌"}.get(r["판단"], "❓")
        print(f"{mark} [{r['매체'] or '?'}] {r['제목'] or r['url']}")
        if r["오류"]:
            print(f"    └ 오류: {r['오류']}")

    # ---- CSV 저장 (엑셀에서 한글 깨지지 않도록 utf-8-sig) ----
    out_path = Path(f"결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f, fieldnames=["순번", "판단", "매체", "제목", "주제", "근거", "url", "오류"]
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"\nCSV 저장 완료: {out_path.resolve()}")


if __name__ == "__main__":
    main()
